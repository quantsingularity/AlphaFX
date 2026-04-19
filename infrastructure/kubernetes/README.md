# AlphaFX Kubernetes Infrastructure

Production-grade Kubernetes manifests for the AlphaFX FX analytics platform.
Built with Kustomize, structured for multi-environment deployments (development and production),
and following industry-standard security and reliability practices.

---

## Directory Structure

```
kubernetes/
  base/                          Shared base manifests
    namespace.yaml               alphafx namespace
    configmap.yaml               Non-sensitive application config
    secret.yaml                  Sensitive credentials (base64 placeholders)
    rbac/
      serviceaccount.yaml        Dedicated ServiceAccount for all pods
      role.yaml                  Least-privilege Role
      rolebinding.yaml           Binds Role to ServiceAccount
    postgres/
      statefulset.yaml           PostgreSQL 16 StatefulSet with PVC
      service.yaml               Headless ClusterIP service
    redis/
      statefulset.yaml           Redis 7 StatefulSet with PVC
      service.yaml               Headless ClusterIP service
    backend/
      deployment.yaml            Django ASGI backend (Daphne), 2 replicas
      service.yaml               ClusterIP service on port 8000
      hpa.yaml                   HorizontalPodAutoscaler (2-10 replicas)
    ai-services/
      deployment.yaml            FastAPI ML microservice (uvicorn), 2 replicas
      service.yaml               ClusterIP service on port 8001
      pvc.yaml                   Shared PVC for trained model files
      hpa.yaml                   HorizontalPodAutoscaler (2-8 replicas)
    frontend/
      deployment.yaml            React SPA served by Nginx, 2 replicas
      service.yaml               ClusterIP service on port 80
    ingress/
      ingress.yaml               nginx Ingress with TLS, CORS, WebSocket support
    policies/
      network-policy.yaml        Default-deny + allow-list NetworkPolicies
      pod-disruption-budget.yaml PodDisruptionBudgets for all components
      resource-quota.yaml        Namespace ResourceQuota and LimitRange
    kustomization.yaml           Base Kustomize entry point
  overlays/
    development/                 Dev overlay: DEBUG=True, 1 replica, smaller limits
      kustomization.yaml
      patches/
        backend-dev.yaml
        ai-services-dev.yaml
        frontend-dev.yaml
    production/                  Prod overlay: pinned tags, 3 replicas, larger limits
      kustomization.yaml
      patches/
        backend-prod.yaml
        ai-services-prod.yaml
        postgres-prod.yaml
  README.md
```

---

## Prerequisites

| Tool                     | Minimum Version | Purpose                                 |
| ------------------------ | --------------- | --------------------------------------- |
| kubectl                  | 1.28            | Cluster interaction                     |
| kustomize                | 5.0             | Manifest templating                     |
| Kubernetes               | 1.28            | Target cluster                          |
| nginx Ingress Controller | 1.10            | Ingress routing                         |
| cert-manager             | 1.14            | TLS certificate provisioning (optional) |
| Container registry       | any             | Image storage                           |

---

## Quick Start

### 1. Configure secrets

Never commit real credentials. Before deploying, replace all placeholder values in
`base/secret.yaml` with properly encoded secrets, or use an external secrets operator.

```bash
# Generate a Django secret key and encode it
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" \
  | tr -d '\n' | base64

# Encode a database password
echo -n "your-secure-db-password" | base64
```

Update `base/secret.yaml` with the encoded values, or configure your secrets manager.

### 2. Update image registry

Replace `registry.example.com/alphafx/` in the overlay `kustomization.yaml` files
with your actual container registry path.

```bash
# Example: build and push images
docker build -t registry.example.com/alphafx/backend:1.0.0 code/backend/
docker build -t registry.example.com/alphafx/ai-services:1.0.0 code/ai_services/
docker build -t registry.example.com/alphafx/frontend:1.0.0 frontend/

docker push registry.example.com/alphafx/backend:1.0.0
docker push registry.example.com/alphafx/ai-services:1.0.0
docker push registry.example.com/alphafx/frontend:1.0.0
```

### 3. Update hostnames

Edit `base/ingress/ingress.yaml` and replace `alphafx.example.com` with your domain.
Update `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` in the overlay `kustomization.yaml` accordingly.

### 4. Deploy

Development:

```bash
kubectl apply -k infrastructure/kubernetes/overlays/development
```

Production:

```bash
kubectl apply -k infrastructure/kubernetes/overlays/production
```

Preview the rendered manifests before applying:

```bash
kubectl kustomize infrastructure/kubernetes/overlays/production
```

---

## Service Topology

```
Internet
   |
   v
[Ingress (nginx)]
   |-- /api/*          --> backend:8000   (Django REST API)
   |-- /ws/*           --> backend:8000   (WebSocket, live FX rates)
   |-- /admin/*        --> backend:8000   (Django Admin)
   |-- /docs/*         --> backend:8000   (OpenAPI docs)
   |-- /ai/*           --> ai-services:8001 (ML inference API)
   |-- /              --> frontend:80     (React SPA)

backend:8000
   |-- postgres:5432   (database reads/writes)
   |-- redis:6379/0    (cache, channel layer for WebSocket)
   |-- ai-services:8001 (ML signal aggregation)

ai-services:8001
   |-- redis:6379/1    (model results cache)
```

---

## Component Details

### Backend (Django + Daphne)

- Runs Django 5 over ASGI via Daphne to support both HTTP and WebSocket connections.
- An init container waits for PostgreSQL readiness before the main container starts.
- A second init container runs `manage.py migrate` on each rollout so schema changes
  are applied exactly once before new pods receive traffic.
- StaticFiles are collected into an `emptyDir` volume at startup.
- Liveness, readiness, and startup probes all target `/health`.
- HPA scales from 2 to 10 replicas based on CPU (70%) and memory (80%) utilization.

### AI Services (FastAPI + uvicorn)

- Runs two uvicorn workers per pod for concurrent inference.
- Trained model files (LSTM, GARCH, HMM, anomaly detectors) are stored on a shared
  `ReadWriteMany` PVC so all replicas load from the same model store.
- Startup probe allows up to 5 minutes for initial model loading.
- HPA scales from 2 to 8 replicas. Scale-down has a 10-minute stabilization window
  to avoid thrashing when models are large.

### Frontend (React SPA + Nginx)

- Multi-stage Docker build: Node.js builds the Vite/React bundle, Nginx serves the dist.
- All unknown paths are handled by Nginx's `try_files` so React Router works correctly.
- Extremely low resource footprint: 50m CPU / 64Mi memory request.

### PostgreSQL

- Deployed as a StatefulSet with a 10Gi `ReadWriteOnce` PVC per pod.
- Headless Service provides stable DNS (`postgres.alphafx.svc.cluster.local`).
- PodDisruptionBudget ensures the single replica is never evicted without replacement.

### Redis

- Deployed as a StatefulSet with AOF persistence enabled (`appendonly yes`).
- Memory capped at 200 MB with `allkeys-lru` eviction policy, matching cache usage.
- Database 0 used by Django cache/channels; database 1 used by AI services.

---

## Security

### RBAC

All pods run under the `alphafx` ServiceAccount. The Role grants only the minimum
permissions required: read access to ConfigMaps and Secrets, and list access to Pods.
`automountServiceAccountToken: false` is set on the ServiceAccount to prevent automatic
token injection into pods that do not need API access.

### Network Policies

A `default-deny-ingress` NetworkPolicy blocks all inbound traffic within the namespace
by default. Explicit allow policies then open only the required paths:

- Ingress controller to backend, ai-services, and frontend
- backend to postgres and redis
- ai-services to redis
- No pod has unrestricted egress within the cluster

### Pod Security

All containers set:

- `runAsNonRoot: true`
- `allowPrivilegeEscalation: false`
- `capabilities: drop: ["ALL"]`

### Secrets Management

The `secret.yaml` in this repository contains only base64-encoded placeholder values.
For production, replace the file entirely or adopt one of:

- Kubernetes External Secrets Operator with AWS Secrets Manager, GCP Secret Manager,
  or HashiCorp Vault as the backend
- Sealed Secrets (Bitnami) for encrypted secrets committed to version control
- ArgoCD Vault Plugin or similar GitOps-native secret injection

---

## Resource Sizing

| Component   | CPU Request | CPU Limit | Memory Request | Memory Limit | Min Replicas | Max Replicas |
| ----------- | ----------- | --------- | -------------- | ------------ | ------------ | ------------ |
| backend     | 250m        | 500m      | 256Mi          | 512Mi        | 2            | 10           |
| ai-services | 500m        | 1000m     | 512Mi          | 2Gi          | 2            | 8            |
| frontend    | 50m         | 100m      | 64Mi           | 128Mi        | 2            | 2            |
| postgres    | 250m        | 500m      | 256Mi          | 512Mi        | 1            | 1            |
| redis       | 100m        | 200m      | 128Mi          | 256Mi        | 1            | 1            |

Production overlay increases backend and ai-services limits and sets 3 base replicas.

---

## Kustomize Overlays

The overlay pattern keeps environment differences explicit and minimal:

```
base            Defines all resources and shared config
overlays/
  development   DEBUG=True, 1 replica, reduced limits, :dev image tags
  production    DEBUG=False, 3 replicas, larger limits, pinned semver image tags
```

To add a new environment (e.g., staging):

```bash
mkdir -p infrastructure/kubernetes/overlays/staging/patches
cp infrastructure/kubernetes/overlays/production/kustomization.yaml \
   infrastructure/kubernetes/overlays/staging/kustomization.yaml
# Edit kustomization.yaml to adjust replica counts, resource limits, and image tags
```

---

## Health Checks and Probes

| Component   | Liveness       | Readiness      | Startup                |
| ----------- | -------------- | -------------- | ---------------------- |
| backend     | GET /health    | GET /health    | GET /health (150s max) |
| ai-services | GET /health    | GET /health    | GET /health (300s max) |
| frontend    | GET /          | GET /          | --                     |
| postgres    | pg_isready     | pg_isready     | --                     |
| redis       | redis-cli ping | redis-cli ping | --                     |

---

## Ingress and TLS

The Ingress resource is configured for the nginx Ingress Controller and assumes
cert-manager is installed with a `letsencrypt-prod` ClusterIssuer. To disable
automatic certificate provisioning, remove the `cert-manager.io/cluster-issuer`
annotation and manage the `alphafx-tls` Secret manually.

WebSocket connections to `/ws/` require HTTP/1.1 upgrade headers. These are set
via the `configuration-snippet` annotation on the Ingress resource.

---

## CI/CD Integration

A typical GitOps pipeline with this layout looks like:

```
git push
  --> CI: build images, run tests, push to registry with commit-sha tag
  --> CD: update image tag in overlay kustomization.yaml
  --> ArgoCD / Flux: detect diff, kubectl apply -k overlays/production
  --> Kubernetes: rolling update (maxUnavailable=0, maxSurge=1)
```

For image tag automation:

```bash
# In CI, update the production image tag after a successful build
cd infrastructure/kubernetes/overlays/production
kustomize edit set image registry.example.com/alphafx/backend=registry.example.com/alphafx/backend:${GIT_SHA}
```

---

## Useful Commands

```bash
# Check rollout status
kubectl rollout status deployment/backend -n alphafx
kubectl rollout status deployment/ai-services -n alphafx

# View logs
kubectl logs -n alphafx -l app=backend --tail=100 -f
kubectl logs -n alphafx -l app=ai-services --tail=100 -f

# Scale manually (bypasses HPA temporarily)
kubectl scale deployment/backend --replicas=4 -n alphafx

# Exec into a backend pod
kubectl exec -it -n alphafx deployment/backend -- bash

# Run a Django management command
kubectl exec -it -n alphafx deployment/backend -- python manage.py shell

# Check HPA status
kubectl get hpa -n alphafx

# View all resources in namespace
kubectl get all -n alphafx

# Rollback a bad deployment
kubectl rollout undo deployment/backend -n alphafx

# Port-forward for local debugging (bypasses Ingress)
kubectl port-forward -n alphafx svc/backend 8000:8000
kubectl port-forward -n alphafx svc/ai-services 8001:8001
kubectl port-forward -n alphafx svc/postgres 5432:5432
```

---

## Troubleshooting

**Pods stuck in Pending**
Check resource quotas and node capacity:

```bash
kubectl describe pod <pod-name> -n alphafx
kubectl describe resourcequota alphafx-quota -n alphafx
```

**Backend CrashLoopBackOff**
Check if PostgreSQL is ready and the SECRET_KEY / DATABASE_URL are correctly set:

```bash
kubectl logs -n alphafx deployment/backend --previous
kubectl exec -n alphafx deployment/backend -- env | grep DATABASE
```

**AI services slow to start**
The startup probe allows 300 seconds for model loading. Check logs for errors:

```bash
kubectl logs -n alphafx deployment/ai-services -f
```

**WebSocket connections dropping**
Ensure the `proxy-read-timeout` and `proxy-send-timeout` annotations on the Ingress
are set to `86400` (24 hours) to prevent the proxy from closing idle streams.

**PVC stuck in Pending**
Verify your cluster has a StorageClass capable of provisioning the required access mode
(`ReadWriteOnce` for Postgres/Redis, `ReadWriteMany` for AI models):

```bash
kubectl get storageclass
kubectl describe pvc -n alphafx
```

---

## Maintenance

**Database backup**
The `scripts/db/backup.sh` script in the project root can be adapted to run as a
Kubernetes CronJob targeting the postgres Pod:

```bash
kubectl exec -n alphafx statefulset/postgres -- \
  pg_dump -U alphafx alphafx | gzip > alphafx_$(date +%Y%m%d).sql.gz
```

**Upgrading PostgreSQL**
StatefulSet upgrades require careful planning. Always take a backup before changing the
image tag. Follow the official PostgreSQL major-version upgrade procedure (pg_upgrade or
dump/restore) when crossing major versions.

**Rotating secrets**
Update the Secret object with new values, then trigger a rollout to pick up the changes:

```bash
kubectl rollout restart deployment/backend -n alphafx
kubectl rollout restart deployment/ai-services -n alphafx
```
