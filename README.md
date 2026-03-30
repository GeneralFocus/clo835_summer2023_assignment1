# CLO835 Final Project — Deployment Guide

## Prerequisites
- AWS CLI configured
- `kubectl` installed and connected to your EKS cluster
- `eksctl` installed
- Docker installed

---

## Step 1 — Placeholders to replace before deploying

Open each file and replace these values:

| File | Placeholder | Replace with |
|---|---|---|
| `k8s/configmap.yaml` | `Your Name Here` | Your actual name |
| `k8s/configmap.yaml` | `your-bucket-name` | Your S3 bucket name |
| `k8s/configmap.yaml` | `background.jpg` | Your image filename in S3 |
| `k8s/secret.yaml` | `cm9vdA==` | `echo -n "youruser" \| base64` |
| `k8s/secret.yaml` | `cGFzc3dvcmQ=` | `echo -n "yourpassword" \| base64` |
| `k8s/serviceaccount.yaml` | `YOUR_ACCOUNT_ID` | Your AWS account ID |
| `k8s/serviceaccount.yaml` | `YOUR_ROLE_NAME` | Your IRSA role name |
| `k8s/flask-deployment.yaml` | `YOUR_ACCOUNT_ID` | Your AWS account ID |
| `k8s/flask-deployment.yaml` | `YOUR_REGION` | e.g. `us-east-1` |
| `k8s/flux-source.yaml` | `YOUR_GITHUB_USERNAME` | Your GitHub username |
| `k8s/flux-source.yaml` | `YOUR_REPO_NAME` | Your GitHub repo name |

---

## Step 2 — Create EKS Cluster

```bash
eksctl create cluster \
  --name final-cluster \
  --region us-east-1 \
  --nodes 2

# Verify
kubectl get nodes
```

---

## Step 3 — Create namespace

```bash
kubectl create namespace final
```

---

## Step 4 — Create S3 bucket and upload background image

```bash
# Create private bucket
aws s3 mb s3://your-bucket-name --region us-east-1

# Upload your background image
aws s3 cp background.jpg s3://your-bucket-name/background.jpg
```

---

## Step 5 — Set up IRSA (IAM Role for Service Account)

```bash
# Enable OIDC provider on the cluster
eksctl utils associate-iam-oidc-provider \
  --cluster final-cluster \
  --region us-east-1 \
  --approve

# Create IAM policy for S3 access
aws iam create-policy \
  --policy-name clo835-s3-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }]
  }'

# Create IAM service account (automatically creates the IAM role and links it)
eksctl create iamserviceaccount \
  --name clo835 \
  --namespace final \
  --cluster final-cluster \
  --region us-east-1 \
  --attach-policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/clo835-s3-policy \
  --approve \
  --override-existing-serviceaccounts
```

> Note: `eksctl create iamserviceaccount` creates the ServiceAccount AND the IAM role automatically.
> You can skip applying `serviceaccount.yaml` separately if you use this command.

---

## Step 6 — Add GitHub Secrets for CI/CD

In your GitHub repo → Settings → Secrets → Actions, add:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` (if using temporary credentials)

---

## Step 7 — Push code to GitHub (triggers CI/CD)

```bash
git add .
git commit -m "feat: add background image, secrets, configmap support"
git push origin main
```

This triggers GitHub Actions which builds and pushes your image to ECR automatically.

---

## Step 8 — Deploy all manifests to EKS

```bash
kubectl apply -f k8s/secret.yaml -n final
kubectl apply -f k8s/configmap.yaml -n final
kubectl apply -f k8s/pvc.yaml -n final
kubectl apply -f k8s/clusterrole.yaml
kubectl apply -f k8s/clusterrolebinding.yaml
kubectl apply -f k8s/mysql-deployment.yaml -n final
kubectl apply -f k8s/mysql-service.yaml -n final
kubectl apply -f k8s/flask-deployment.yaml -n final
kubectl apply -f k8s/flask-service.yaml -n final
```

---

## Step 9 — Verify everything is running

```bash
# Check pods
kubectl get pods -n final

# Check services
kubectl get svc -n final

# Get the external URL of your app
kubectl get svc flask-service -n final
```

Wait until all pods show `Running` status, then open the EXTERNAL-IP in your browser.

---

## Step 10 — Test ConfigMap background image update

```bash
# Upload new image to S3
aws s3 cp new-background.jpg s3://your-bucket-name/new-background.jpg

# Update the ConfigMap
kubectl edit configmap app-configmap -n final
# Change BG_IMAGE_URL to s3://your-bucket-name/new-background.jpg

# Restart Flask pods to pick up the new value
kubectl rollout restart deployment/flask-deployment -n final

# Watch pods restart
kubectl get pods -n final -w
```

---

## Step 11 (Bonus) — Install Metrics Server and deploy HPA

```bash
# Install metrics server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Deploy HPA
kubectl apply -f k8s/hpa.yaml -n final

# Watch HPA
kubectl get hpa -n final -w

# Generate load to trigger scaling (run in a separate terminal)
kubectl run load-test --image=busybox --rm -it --restart=Never -- \
  /bin/sh -c "while true; do wget -q -O- http://flask-service.final.svc.cluster.local; done"
```

---

## Step 12 (Bonus) — Set up Flux GitOps

```bash
# Install Flux CLI
curl -s https://fluxcd.io/install.sh | sudo bash

# Bootstrap Flux with your GitHub repo
flux bootstrap github \
  --owner=YOUR_GITHUB_USERNAME \
  --repository=YOUR_REPO_NAME \
  --branch=main \
  --path=./clusters/final \
  --personal

# Apply the GitRepository and Kustomization
kubectl apply -f k8s/flux-source.yaml -n flux-system

# Watch Flux sync
flux get kustomizations --watch
```

---

## Cleanup (after demo/submission)

```bash
# Delete cluster (also deletes all nodes and load balancers — saves AWS costs!)
eksctl delete cluster --name final-cluster --region us-east-1
```
