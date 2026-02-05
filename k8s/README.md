# Kubernetes Deployment Files

This directory contains all the Kubernetes manifests needed to deploy the Slack FAQ bot.

## Files

- **namespace.yaml**: Creates the `faq-bot` namespace
- **configmap.yaml**: Contains the FAQ content (from faq.md)
- **deployment.yaml**: Main deployment manifest with pod configuration
- **secret.yaml.template**: Template for secrets (DO NOT commit with real values)

## Deployment Instructions

### Prerequisites

1. Docker Hub account
2. kubectl configured for your Kubernetes cluster
3. Slack tokens and Anthropic API key ready

### Step 1: Build and Push Container

```bash
# Update <your-dockerhub-username> in deployment.yaml first
docker build -t <your-dockerhub-username>/faq-bot:v1.0.0 .
docker push <your-dockerhub-username>/faq-bot:v1.0.0
```

### Step 2: Update Configuration

1. Edit `deployment.yaml`:
   - Replace `<your-dockerhub-username>` with your Docker Hub username
   - Replace `SLACK_ALLOWED_CHANNELS` value with your actual channel IDs

### Step 3: Deploy to Kubernetes

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create secrets (IMPORTANT: Use kubectl, not the template file)
kubectl create secret generic faq-bot-secrets \
  --namespace=faq-bot \
  --from-literal=slack-bot-token="xoxb-YOUR-ACTUAL-TOKEN" \
  --from-literal=slack-app-token="xapp-YOUR-ACTUAL-TOKEN" \
  --from-literal=anthropic-api-key="sk-ant-YOUR-ACTUAL-KEY"

# 3. Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# 4. Deploy the bot
kubectl apply -f k8s/deployment.yaml

# 5. Verify deployment
kubectl get pods -n faq-bot
kubectl logs -f deployment/faq-bot -n faq-bot
```

## Updating the Deployment

### Update FAQ Content

```bash
# Edit configmap.yaml, then:
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/faq-bot -n faq-bot
```

### Update Code

```bash
# Build new version
docker build -t <your-dockerhub-username>/faq-bot:v1.1.0 .
docker push <your-dockerhub-username>/faq-bot:v1.1.0

# Update deployment
kubectl set image deployment/faq-bot \
  faq-bot=<your-dockerhub-username>/faq-bot:v1.1.0 \
  -n faq-bot
```

### Rotate Secrets

```bash
# Create new secret (overwrites existing)
kubectl create secret generic faq-bot-secrets \
  --namespace=faq-bot \
  --from-literal=slack-bot-token="NEW_TOKEN" \
  --from-literal=slack-app-token="NEW_TOKEN" \
  --from-literal=anthropic-api-key="NEW_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pod to pick up new secrets
kubectl rollout restart deployment/faq-bot -n faq-bot
```

## Troubleshooting

### View logs
```bash
kubectl logs -f deployment/faq-bot -n faq-bot
```

### Check pod status
```bash
kubectl get pods -n faq-bot
kubectl describe pod -n faq-bot <pod-name>
```

### Rollback deployment
```bash
kubectl rollout undo deployment/faq-bot -n faq-bot
```

## Security Notes

- **NEVER commit real secrets to git**
- The `secret.yaml.template` file is for reference only
- Always create secrets using `kubectl create secret` command
- `k8s/secret.yaml` is in `.gitignore` to prevent accidental commits
