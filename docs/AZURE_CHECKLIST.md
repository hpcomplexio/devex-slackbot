# Azure Deployment Checklist

Use this checklist to deploy your FAQ bot to Azure step-by-step.

## Prerequisites ✓

- [ ] Azure account with active subscription
- [ ] Azure CLI installed (`az --version`)
- [ ] kubectl installed (`kubectl version --client`)
- [ ] Docker installed and running (`docker --version`)
- [ ] Have ready:
  - [ ] Slack Bot Token (xoxb-...)
  - [ ] Slack App Token (xapp-...)
  - [ ] Anthropic API Key (sk-ant-...)
  - [ ] Slack Channel IDs (C...)

## Step 1: Azure Login ✓

```bash
az login
az account set --subscription "<Your-Subscription-ID>"
```

- [ ] Logged into Azure
- [ ] Correct subscription selected

## Step 2: Create Resource Group ✓

```bash
az group create --name faq-bot-rg --location eastus
```

- [ ] Resource group created
- [ ] Region: ___________

## Step 3: Create Azure Container Registry ✓

```bash
# Replace <unique-name> with your own (lowercase alphanumeric only)
export ACR_NAME="<your-unique-acr-name>"

az acr create \
  --resource-group faq-bot-rg \
  --name $ACR_NAME \
  --sku Basic \
  --location eastus

az acr update --name $ACR_NAME --admin-enabled true

# Save this output
az acr show --name $ACR_NAME --query loginServer --output tsv
```

- [ ] ACR created
- [ ] ACR name: ___________
- [ ] Login server saved: ___________.azurecr.io

## Step 4: Build and Push Docker Image ✓

```bash
cd /path/to/devex-slackbot

az acr login --name $ACR_NAME

docker build -t $ACR_NAME.azurecr.io/faq-bot:v1.0.0 .

docker push $ACR_NAME.azurecr.io/faq-bot:v1.0.0

# Verify
az acr repository list --name $ACR_NAME --output table
```

- [ ] Image built successfully
- [ ] Image pushed to ACR
- [ ] Image shows in repository list

## Step 5: Create AKS Cluster ✓

```bash
az aks create \
  --resource-group faq-bot-rg \
  --name faq-bot-aks \
  --node-count 1 \
  --node-vm-size Standard_B2s \
  --enable-managed-identity \
  --attach-acr $ACR_NAME \
  --generate-ssh-keys
```

⏱️ This takes 5-10 minutes

- [ ] AKS cluster created
- [ ] ACR attached to AKS

## Step 6: Connect kubectl ✓

```bash
az aks get-credentials \
  --resource-group faq-bot-rg \
  --name faq-bot-aks

kubectl get nodes
```

- [ ] kubectl configured
- [ ] Node shows as "Ready"

## Step 7: Update Kubernetes Manifests ✓

Edit `k8s/deployment.yaml`:

```yaml
# Line 23 - Update image
image: <your-acr-name>.azurecr.io/faq-bot:v1.0.0

# Line 47 - Update channels
value: "C123456789,C987654321"  # Your actual channel IDs
```

- [ ] Image path updated in deployment.yaml
- [ ] Channel IDs updated in deployment.yaml

## Step 8: Deploy to Kubernetes ✓

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (REPLACE WITH YOUR ACTUAL VALUES)
kubectl create secret generic faq-bot-secrets \
  --namespace=faq-bot \
  --from-literal=slack-bot-token="xoxb-YOUR-TOKEN" \
  --from-literal=slack-app-token="xapp-YOUR-TOKEN" \
  --from-literal=anthropic-api-key="sk-ant-YOUR-KEY"

# Deploy FAQ content
kubectl apply -f k8s/configmap.yaml

# Deploy bot
kubectl apply -f k8s/deployment.yaml

# Wait for deployment
kubectl rollout status deployment/faq-bot -n faq-bot
```

- [ ] Namespace created
- [ ] Secrets created
- [ ] ConfigMap applied
- [ ] Deployment applied
- [ ] Rollout completed

## Step 9: Verify Deployment ✓

```bash
# Check pod status (should be Running)
kubectl get pods -n faq-bot

# View logs
kubectl logs -f deployment/faq-bot -n faq-bot
```

- [ ] Pod is in "Running" status
- [ ] Logs show bot initialization
- [ ] No error messages in logs

## Step 10: Test in Slack ✓

- [ ] Go to one of your configured Slack channels
- [ ] Send a test question (e.g., "How do I...?")
- [ ] Bot responds in thread
- [ ] Answer is relevant and includes source

## Troubleshooting

### Pod not starting?
```bash
kubectl describe pod -n faq-bot <pod-name>
kubectl logs deployment/faq-bot -n faq-bot
```

### Bot not responding in Slack?
1. Check logs for errors
2. Verify tokens are correct
3. Verify channel IDs match
4. Ensure bot is invited to channels (`/invite @FAQ Bot`)

### Need to update something?
```bash
# Update code
docker build -t $ACR_NAME.azurecr.io/faq-bot:v1.1.0 .
docker push $ACR_NAME.azurecr.io/faq-bot:v1.1.0
kubectl set image deployment/faq-bot faq-bot=$ACR_NAME.azurecr.io/faq-bot:v1.1.0 -n faq-bot

# Update FAQ content
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/faq-bot -n faq-bot

# Rotate secrets
kubectl delete secret faq-bot-secrets -n faq-bot
kubectl create secret generic faq-bot-secrets --namespace=faq-bot --from-literal=...
kubectl rollout restart deployment/faq-bot -n faq-bot
```

## Monitoring

```bash
# View live logs
kubectl logs -f deployment/faq-bot -n faq-bot

# Check resource usage
kubectl top pods -n faq-bot

# Check pod status
kubectl get pods -n faq-bot
```

## Success! 🎉

Your FAQ bot is now running 24/7 on Azure!

### Monthly Cost
- AKS: ~$73
- VM (Standard_B2s): ~$30
- ACR: ~$5
- **Total: ~$110/month**

### Next Steps
- Monitor logs for the first few hours
- Test various questions in Slack
- Update FAQ content as needed
- Consider setting up Azure Monitor for alerts

## Cleanup (When Done)

```bash
# Delete everything
az group delete --name faq-bot-rg --yes --no-wait
```

---

For detailed information, see [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md)
