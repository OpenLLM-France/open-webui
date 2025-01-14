"""Stack Pulumi pour le déploiement de Lucie Queue."""

import pulumi
import pulumi_docker as docker
from pulumi_docker import DockerBuild

config = pulumi.Config()

stack = pulumi.get_stack()
project = pulumi.get_project()

# Configuration Redis
redis_network = docker.Network(
    "redis-network",
    name=f"queue-network-{stack}",
    driver="bridge"
)

redis = docker.Container(
    "redis",
    name=f"redis-{stack}",
    image="redis:alpine",
    ports=[{"internal": 6379, "external": 6379}],
    networks_advanced=[{
        "name": redis_network.name,
        "aliases": ["redis"]
    }],
    command=["redis-server", "--appendonly", "yes"],
    healthcheck={
        "test": ["CMD", "redis-cli", "ping"],
        "interval": "30s",
        "timeout": "10s",
        "retries": 3
    }
)

# Configuration Celery
celery_image = docker.RemoteImage(
    "celery-worker",
    name=f"{project}/celery-worker:{stack}",
    build=DockerBuild(
        context=".",
        dockerfile="Dockerfile.celery"
    )
)

celery = docker.Container(
    "celery",
    name=f"celery-{stack}",
    image=celery_image.name,
    environment={
        "REDIS_HOST": "redis",
        "CELERY_BROKER_URL": "redis://redis:6379",
        "CELERY_RESULT_BACKEND": "redis://redis:6379"
    },
    networks_advanced=[{
        "name": redis_network.name
    }],
    depends_on=[redis.name]
)

# Configuration API
api_image = docker.RemoteImage(
    "api",
    name=f"{project}/api:{stack}",
    build=DockerBuild(
        context=".",
        dockerfile="Dockerfile"
    )
)

api = docker.Container(
    "api",
    name=f"api-{stack}",
    image=api_image.name,
    ports=[{"internal": 8000, "external": 8000}],
    environment={
        "REDIS_HOST": "redis",
        "CELERY_BROKER_URL": "redis://redis:6379",
        "CELERY_RESULT_BACKEND": "redis://redis:6379"
    },
    networks_advanced=[{
        "name": redis_network.name
    }],
    healthcheck={
        "test": ["CMD", "curl", "-f", "http://localhost:8000/queue/metrics"],
        "interval": "30s",
        "timeout": "10s",
        "retries": 3
    },
    depends_on=[redis.name, celery.name]
)

# Exports
pulumi.export('redis_url', f"redis://localhost:6379")
pulumi.export('api_url', f"http://localhost:8000") 