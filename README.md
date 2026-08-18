# Employee Churn Prediction API

A FastAPI service that generates an employee churn-risk assessment from employee data stored in a database view. The service uses Azure OpenAI to return a likelihood score, a risk category, an explanation of contributing factors, and an AI confidence score.

## Features

- Predicts churn risk for an employee identified by ID.
- Reads employee data from the `EmployeeDetails_view` database view.
- Handles incomplete employee records: missing values are marked as `Not provided` for the model instead of rejecting the request.
- Returns an AI confidence score from 1 to 100. Confidence reflects the completeness and quality of the available employee data; it is not the likelihood of churn.
- Uses JSON-mode Azure OpenAI responses with a tolerant text fallback, preventing minor response-format differences from producing `N/A` output.
- Includes a Docker image definition and GitHub Actions workflows for validation and container-image publishing.

## Architecture

```text
Client
  |
  | POST /predict/{employee_id}
  v
FastAPI application
  |
  +--> Database: EmployeeDetails_view
  |
  +--> Data processing: derive age and tenure; identify missing predictors
  |
  +--> Azure OpenAI: churn likelihood, confidence, summary, feature analysis
  |
  v
JSON response
```

## Requirements

- Python 3.12 (the Docker image uses Python 3.12)
- Access to a MySQL-compatible database containing `EmployeeDetails_view`
- An Azure OpenAI deployment that supports Chat Completions JSON mode
- Docker Desktop, if running the containerized service

## Setup

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy the environment template and add the real values:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`; it contains credentials and is excluded by `.dockerignore`.

### Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `AZURE_OPENAI_API_KEY` | Yes | Azure OpenAI API key. |
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI endpoint, for example `https://your-resource.openai.azure.com/`. |
| `AZURE_OPENAI_API_VERSION` | Yes | Azure OpenAI API version enabled by the resource. |
| `AZURE_OPENAI_MODEL` | Yes | Azure deployment name, not necessarily the base model name. |
| `DB_URI` | Yes | SQLAlchemy MySQL connection URI, including any required SSL options. |
| `HOST` | No | Listening host. Defaults to `0.0.0.0`. |
| `PORT` | No | Listening port. Defaults to `8000`. |

Example `DB_URI` format:

```text
mysql+pymysql://USERNAME:PASSWORD@HOST:3306/DATABASE
```

## Run locally

```powershell
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Open interactive API documentation at `http://localhost:8000/docs`.

## Docker

Build and run the image:

```powershell
docker build -t employee-churn-api:local .
docker run --env-file .env --publish 8000:8000 employee-churn-api:local
```

The application is then available at `http://localhost:8000`. Environment variables are supplied at runtime; no secrets are copied into the image.

## API

### Health check

```http
GET /
```

Response:

```json
{
  "status": "API is running"
}
```

### Generate a prediction

```http
POST /predict/{employee_id}
```

Example:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/predict/123
```

Successful response:

```json
{
  "employee_id": 123,
  "likelihood": 61.5,
  "category": "Likely to churn",
  "summary": "The employee has several indicators associated with retention risk.",
  "feature_analysis": "Short tenure and a low performance score increase churn risk.",
  "ai_confidence": 72
}
```

`likelihood` is a percentage from 0 to 100. Categories are calculated by the API:

| Likelihood | Category |
| --- | --- |
| Less than 25 | Not likely to churn |
| 25–50 | Less likely to churn |
| Over 50–75 | Likely to churn |
| Over 75 | Very likely to churn |

### Missing data and confidence

The prediction route does not fail solely because one or more predictor values are missing. Null, invalid derived dates, and blank string values are labelled `Not provided` in the model input, and the missing field names are included explicitly. The model is instructed to lower `ai_confidence` when essential inputs—such as performance, potential, compensation, tenure, or work-pattern data—are absent.

AI-generated scores are decision-support information, not a substitute for HR review. Avoid using the result as the sole basis for an employment decision.

## Data expectations

The database view is expected to include `Employee ID`, `Work Status`, name and employment-date fields, and the prediction fields used by the service:

```text
Gender, Marital Status, Department, Designation, Grade, Employment Type,
Work Model, Number Of Days Per Week, Leave Length, Payroll Type, Monthly Gross,
Salary Frequency, Performance Score, Potential Score
```

`Age` and `tenure_at_company` are derived from `Date Of Birth` and `Hire Date` respectively.

## CI/CD

GitHub Actions workflows are located in `.github/workflows/`.

- `ci.yml` runs on pushes and pull requests to `main`. It installs dependencies, checks that the source compiles, and validates that the Docker image builds.
- `docker-publish.yml` runs after successful CI on `main`. It builds the image, publishes it to Azure Container Registry (ACR), and rolls it out to Azure Kubernetes Service (AKS).

Azure images use:

```text
aiperformanceregistry.azurecr.io/employee-churn:<tag>
```

### Azure deployment

The delivery workflow targets:

| Resource | Value |
| --- | --- |
| Subscription | Microsoft Azure Sponsorship (Hcmatrix3.0) |
| Resource group | `Churn_prediction` |
| Container registry | `AIPerformanceRegistry` (`aiperformanceregistry.azurecr.io`) |
| AKS cluster | `AI-Performance-Module-Cluster` |
| Kubernetes namespace | `churn-prediction` |

Before the first deployment, complete these one-time setup steps from an Azure CLI session authenticated to the subscription:

```powershell
az account set --subscription "Microsoft Azure Sponsorship (Hcmatrix3.0)"
az aks update --resource-group Churn_prediction --name AI-Performance-Module-Cluster --attach-acr AIPerformanceRegistry
az aks get-credentials --resource-group Churn_prediction --name AI-Performance-Module-Cluster --overwrite-existing
Copy-Item k8s/secret.example.yaml k8s/secret.yaml
# Edit k8s/secret.yaml with real Azure OpenAI and database credentials.
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml
```

`--attach-acr` grants the AKS kubelet identity permission to pull images from ACR. It requires sufficient Azure RBAC privileges.

Configure GitHub Actions Azure OpenID Connect (OIDC) with a federated credential restricted to this repository and its `main` branch. Add these GitHub repository secrets:

| Secret | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID` | Application/client ID of the Azure AD workload identity. |
| `AZURE_TENANT_ID` | Azure AD tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID (GUID, not subscription display name). |

The Azure workload identity needs permission to push to ACR, obtain AKS credentials, and update the deployment. Assign the least-privileged Azure RBAC roles suitable for the environment; `AcrPush` is needed for the registry, while `Azure Kubernetes Service Cluster User Role` is needed to retrieve cluster user credentials. AKS pulls images through its attached managed identity.

The Kubernetes resources are in `k8s/`. The service is `ClusterIP` by default, keeping the API inside the cluster. Expose it through an approved ingress controller or change `k8s/service.yaml` to `LoadBalancer` if a public endpoint is intended.

## Project layout

```text
src/
  main.py              FastAPI routes and application entry point
  data_processing.py   Database reads, feature derivation, missing-value handling
  prediction.py        Azure OpenAI request and response parsing
  db.py                SQLAlchemy database engine
  config.py            Environment-based configuration
.github/workflows/     CI and container delivery workflows
Dockerfile             Production container definition
requirements.txt       Python dependencies
```
