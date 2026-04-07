act -W .github/workflows/verify-devcontainer.yml \
  --job validate \
  --bind \
  --env CI=true \
  --rm \
  --container-architecture linux/amd64 \
  --platform ubuntu-latest=catthehacker/ubuntu:act-24.04