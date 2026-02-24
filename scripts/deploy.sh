#!/bin/bash
set -e

# Configuration
ACR_NAME="devexslackbotacr"
IMAGE_NAME="faq-bot"
VERSION="v1.3.0"
FULL_IMAGE="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${VERSION}"

echo "🚀 Deploying FAQ Bot ${VERSION}"
echo "================================"

# Check if logged into Azure
echo "📋 Checking Azure login..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged into Azure. Please run 'az login' first."
    exit 1
fi

# Login to ACR
echo "🔐 Logging into Azure Container Registry..."
az acr login --name ${ACR_NAME}

# Build the Docker image
echo "🏗️  Building Docker image..."
docker build -t ${FULL_IMAGE} .

# Push to ACR
echo "📤 Pushing image to ACR..."
docker push ${FULL_IMAGE}

# Apply Kubernetes configurations
echo "☸️  Applying Kubernetes configurations..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml

# Wait for rollout
echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/faq-bot -n faq-bot --timeout=300s

# Show pod status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Current pod status:"
kubectl get pods -n faq-bot

echo ""
echo "📝 To view logs:"
echo "   kubectl logs -f deployment/faq-bot -n faq-bot"
echo ""
echo "🔍 To check pod details:"
echo "   kubectl describe pod -n faq-bot -l app=faq-bot"
