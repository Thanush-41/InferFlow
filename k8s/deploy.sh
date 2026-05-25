#!/bin/bash
# Deploy InferFlow to a self-hosted Kubernetes cluster
# Prerequisites: kubectl configured, cluster access, nginx-ingress-controller installed

set -e

echo "==> Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "==> Deploying secrets and config..."
kubectl apply -f k8s/config.yaml

echo "==> Deploying PostgreSQL..."
kubectl apply -f k8s/postgres.yaml

echo "==> Waiting for PostgreSQL to be ready..."
kubectl -n inferflow wait --for=condition=Ready pod -l app=postgres --timeout=120s

echo "==> Deploying Redis..."
kubectl apply -f k8s/redis.yaml

echo "==> Waiting for Redis to be ready..."
kubectl -n inferflow wait --for=condition=Ready pod -l app=redis --timeout=60s

echo "==> Building and loading images (for local clusters like k3s/minikube)..."
echo "    If using a registry, push images first and update image references."

# Build images
docker build -t inferflow-backend:latest -f backend/Dockerfile .
docker build -t inferflow-frontend:latest -f frontend/Dockerfile ./frontend

echo "==> Deploying Backend..."
kubectl apply -f k8s/backend.yaml

echo "==> Deploying Frontend..."
kubectl apply -f k8s/frontend.yaml

echo "==> Configuring Ingress..."
kubectl apply -f k8s/ingress.yaml

echo "==> Waiting for all pods to be ready..."
kubectl -n inferflow wait --for=condition=Ready pod --all --timeout=180s

echo ""
echo "✅ InferFlow deployed successfully!"
echo ""
echo "Pods:"
kubectl -n inferflow get pods
echo ""
echo "Services:"
kubectl -n inferflow get svc
echo ""
echo "Ingress:"
kubectl -n inferflow get ingress
echo ""
echo "Update your DNS or /etc/hosts to point inferflow.example.com to your cluster's ingress IP."
