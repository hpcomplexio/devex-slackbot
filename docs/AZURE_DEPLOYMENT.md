# Azure Deployment Guide

This guide walks you through deploying the Slack FAQ Bot to Azure Kubernetes Service (AKS) for continuous 24/7 operation.

## Architecture

```
Azure Container Registry (ACR) → Azure Kubernetes Service (AKS)
                                        ↓
                                   FAQ Bot Pod
                                   (Always Running)
```

## Prerequisites

1. **Azure Account**: Active Azure subscription ([Free trial available](https://azure.microsoft.com/free/))
2. **Azure CLI**: Install from https://docs.microsoft.com/cli/azure/install-azure-cli
3. **kubectl**: Install from https://kubernetes.io/docs/tasks/tools/
4. **Docker**: For building the container image
5. **Credentials Ready**:
   - Slack Bot Token (xoxb-...)
   - Slack App Token (xapp-...)
   - Anthropic API Key (sk-ant-...)
   - Channel IDs for allowed channels

## Step 1: Azure Setup

### 1.1 Login to Azure

```bash
# Login
az login

# Set your subscription (if you have multiple)
az account list --output table
az account set --subscription "<Your-Subscription-ID>"

# Verify
az account show
```

### 1.2 Create Resource Group

```bash
# Create a resource group in your preferred region
az group create \
  --name faq-bot-rg \
  --location eastus

# Available regions: eastus, westus2, centralus, westeurope, etc.
# Check available regions: az account list-locations --output table
```

## Step 2: Create Azure Container Registry (ACR)

ACR stores your Docker images privately within Azure.

```bash
# Create ACR (name must be globally unique, lowercase alphanumeric only)
az acr create \
  --resource-group faq-bot-rg \
  --name <your-unique-acr-name> \
  --sku Basic \
  --location eastus

# Example: az acr create --resource-group faq-bot-rg --name myfaqbotacr --sku Basic --location eastus

# Enable admin access (for easy authentication)
az acr update \
  --name <your-unique-acr-name> \
  --admin-enabled true

# Get ACR login server (save this for later)
az acr show \
  --name <your-unique-acr-name> \
  --query loginServer \
  --output tsv
# Output example: myfaqbotacr.azurecr.io
```

## Step 3: Build and Push Docker Image to ACR

### 3.1 Login to ACR

```bash
# Login to your container registry
az acr login --name <your-unique-acr-name>
```

### 3.2 Build and Push Image

```bash
# Navigate to your project root
cd /path/to/devex-slackbot

# Build image with ACR tag
docker build -t <your-acr-name>.azurecr.io/faq-bot:v1.0.0 .

# Example: docker build -t myfaqbotacr.azurecr.io/faq-bot:v1.0.0 .

# Push to ACR
docker push <your-acr-name>.azurecr.io/faq-bot:v1.0.0

# Verify image was pushed
az acr repository list --name <your-unique-acr-name> --output table
```

## Step 4: Create AKS Cluster

### 4.1 Create AKS Cluster

```bash
# Create a small AKS cluster (1 node is sufficient for this bot)
az aks create \
  --resource-group faq-bot-rg \
  --name faq-bot-aks \
  --node-count 1 \
  --node-vm-size Standard_B2s \
  --enable-managed-identity \
  --attach-acr <your-unique-acr-name> \
  --generate-ssh-keys

# This takes ~5-10 minutes
# Standard_B2s: 2 vCPUs, 4GB RAM (~$30/month)
```

### 4.2 Connect kubectl to AKS

```bash
# Get credentials
az aks get-credentials \
  --resource-group faq-bot-rg \
  --name faq-bot-aks

# Verify connection
kubectl get nodes
# You should see 1 node in Ready status
```

## Step 5: Update Kubernetes Manifests for Azure

### 5.1 Update deployment.yaml

Edit `k8s/deployment.yaml` and update the image path:

```yaml
# Line 23 - Update to use your ACR image
image: <your-acr-name>.azurecr.io/faq-bot:v1.0.0

# Line 47 - Update with your actual channel IDs
- name: SLACK_ALLOWED_CHANNELS
  value: "C123456789,C987654321"  # Your channel IDs
```

## Step 6: Deploy to AKS

### 6.1 Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 6.2 Create Secrets

```bash
# Create secrets with your actual tokens
kubectl create secret generic faq-bot-secrets \
  --namespace=faq-bot \
  --from-literal=slack-bot-token="xoxb-YOUR-ACTUAL-TOKEN" \
  --from-literal=slack-app-token="xapp-YOUR-ACTUAL-TOKEN" \
  --from-literal=anthropic-api-key="sk-ant-YOUR-ACTUAL-KEY"

# Verify secret was created
kubectl get secrets -n faq-bot
```

### 6.3 Deploy ConfigMap and Application

```bash
# Deploy FAQ content
kubectl apply -f k8s/configmap.yaml

# Deploy the bot
kubectl apply -f k8s/deployment.yaml

# Wait for deployment to complete
kubectl rollout status deployment/faq-bot -n faq-bot
```

### 6.4 Verify Deployment

```bash
# Check pod status
kubectl get pods -n faq-bot

# Expected output:
# NAME                       READY   STATUS    RESTARTS   AGE
# faq-bot-xxxxxxxxxx-xxxxx   1/1     Running   0          30s

# View logs
kubectl logs -f deployment/faq-bot -n faq-bot

# You should see initialization logs and "Bot is running!" message
```

## Step 7: Monitor and Maintain

### View Logs

```bash
# Follow live logs
kubectl logs -f deployment/faq-bot -n faq-bot

# View last 100 lines
kubectl logs deployment/faq-bot -n faq-bot --tail=100

# View logs from specific time
kubectl logs deployment/faq-bot -n faq-bot --since=1h
```

### Check Pod Status

```bash
# Get pod status
kubectl get pods -n faq-bot

# Describe pod for detailed info
kubectl describe pod -n faq-bot <pod-name>

# Get pod events
kubectl get events -n faq-bot --sort-by='.lastTimestamp'
```

### Check Resource Usage

```bash
# View CPU/memory usage
kubectl top pods -n faq-bot

# View node usage
kubectl top nodes
```

## Updating Your Deployment

### Update FAQ Content

```bash
# Edit k8s/configmap.yaml with new FAQ content
# Then apply:
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/faq-bot -n faq-bot
```

### Update Code

```bash
# 1. Build new version
docker build -t <your-acr-name>.azurecr.io/faq-bot:v1.1.0 .

# 2. Push to ACR
az acr login --name <your-unique-acr-name>
docker push <your-acr-name>.azurecr.io/faq-bot:v1.1.0

# 3. Update deployment
kubectl set image deployment/faq-bot \
  faq-bot=<your-acr-name>.azurecr.io/faq-bot:v1.1.0 \
  -n faq-bot

# 4. Watch rollout
kubectl rollout status deployment/faq-bot -n faq-bot
```

### Rotate Secrets

```bash
# Delete old secret
kubectl delete secret faq-bot-secrets -n faq-bot

# Create new secret
kubectl create secret generic faq-bot-secrets \
  --namespace=faq-bot \
  --from-literal=slack-bot-token="NEW_TOKEN" \
  --from-literal=slack-app-token="NEW_TOKEN" \
  --from-literal=anthropic-api-key="NEW_KEY"

# Restart to pick up new secrets
kubectl rollout restart deployment/faq-bot -n faq-bot
```

## Troubleshooting

### Pod is not starting

```bash
# Check pod status
kubectl describe pod -n faq-bot <pod-name>

# Common issues:
# - Image pull errors: Verify ACR is attached to AKS
# - Missing secrets: Verify secrets exist and have correct keys
# - Resource limits: Check if node has enough resources
```

### Bot not responding in Slack

1. Check logs for errors:
   ```bash
   kubectl logs deployment/faq-bot -n faq-bot
   ```

2. Verify tokens are correct:
   ```bash
   kubectl get secret faq-bot-secrets -n faq-bot -o yaml
   # Values are base64 encoded
   ```

3. Verify channel IDs in deployment

### Out of Memory / High CPU

```bash
# Check resource usage
kubectl top pods -n faq-bot

# Increase resources in k8s/deployment.yaml:
# resources:
#   requests:
#     memory: "1Gi"    # Increase from 512Mi
#     cpu: "500m"      # Increase from 250m
#   limits:
#     memory: "2Gi"
#     cpu: "1000m"

# Apply changes
kubectl apply -f k8s/deployment.yaml
```

## Cost Management

### Estimated Monthly Costs (East US)

- **AKS Cluster**: ~$0.10/hour ($73/month) for cluster management
- **VM (Standard_B2s)**: ~$30/month for 1 node
- **ACR Basic**: ~$5/month
- **Data Transfer**: Minimal (< $1/month)
- **Total**: ~$110/month

### Cost Optimization Tips

1. **Use smaller VM**: Standard_B1s (1 vCPU, 1GB) for ~$15/month if traffic is low
2. **Stop cluster when not needed**:
   ```bash
   az aks stop --name faq-bot-aks --resource-group faq-bot-rg
   az aks start --name faq-bot-aks --resource-group faq-bot-rg
   ```
3. **Use Azure Calculator**: https://azure.microsoft.com/pricing/calculator/

## Cleanup (Delete Everything)

```bash
# Delete the entire resource group (removes everything)
az group delete --name faq-bot-rg --yes --no-wait

# This removes:
# - AKS cluster
# - ACR
# - All associated resources
```

## Next Steps

- **Set up monitoring**: Use Azure Monitor for container insights
- **Configure auto-scaling**: Add horizontal pod autoscaler
- **Enable backups**: Backup cluster configuration
- **Set up CI/CD**: Automate deployments with GitHub Actions

## Support

- [Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)
- [Azure Container Registry Documentation](https://docs.microsoft.com/azure/container-registry/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
