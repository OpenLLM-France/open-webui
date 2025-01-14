"""Stack Pulumi résiliente avec proxies pour Lucie Queue."""

import pulumi
import pulumi_docker as docker
from pulumi_docker import DockerBuild
from typing import Dict, List

class ServiceProxy:
    """Proxy résilient pour un service."""
    
    def __init__(self, name: str, network: docker.Network, dependencies: List[str] = None):
        self.name = name
        self.network = network
        self.dependencies = dependencies or []
        
        self.proxy = docker.Container(
            f"{name}-proxy",
            name=f"{name}-proxy",
            image="traefik:v2.10",
            command=[
                "--api.insecure=true",
                "--providers.docker=true",
                "--providers.docker.exposedbydefault=false"
            ],
            ports=[
                {"internal": 80, "external": 80},
                {"internal": 8080, "external": 8080}
            ],
            networks_advanced=[{
                "name": network.name,
                "aliases": [f"{name}-proxy"]
            }],
            restart="always",
            volumes=[
                "/var/run/docker.sock:/var/run/docker.sock:ro"
            ],
            labels={
                "traefik.enable": "true",
                f"traefik.http.services.{name}.loadbalancer.server.port": "80"
            }
        )

class ResilientService:
    """Service avec proxy et health check."""
    
    def __init__(
        self,
        name: str,
        image: str,
        network: docker.Network,
        environment: Dict[str, str] = None,
        health_check: Dict = None,
        dependencies: List[str] = None
    ):
        self.name = name
        self.proxy = ServiceProxy(name, network, dependencies)
        
        default_health = {
            "test": ["CMD", "wget", "--spider", "http://localhost:80"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 3,
            "start_period": "30s"
        }
        
        self.container = docker.Container(
            name,
            name=name,
            image=image,
            networks_advanced=[{
                "name": network.name,
                "aliases": [name]
            }],
            environment=environment or {},
            healthcheck=health_check or default_health,
            restart="unless-stopped",
            labels={
                "traefik.enable": "true",
                f"traefik.http.routers.{name}.rule": f"PathPrefix(`/{name}`)",
                f"traefik.http.services.{name}.loadbalancer.server.port": "80"
            }
        )

class ResilientStack:
    """Stack résiliente avec services proxifiés."""
    
    def __init__(self, stack_name: str):
        self.stack_name = stack_name
        
        self.network = docker.Network(
            "resilient-network",
            name=f"resilient-network-{stack_name}",
            driver="bridge"
        )
        
        # Service Redis avec proxy
        self.redis = ResilientService(
            "redis",
            "redis:alpine",
            self.network,
            health_check={
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 3
            }
        )
        
        # Service Celery avec proxy
        self.celery = ResilientService(
            "celery",
            f"lucie-queue/celery-worker:{stack_name}",
            self.network,
            environment={
                "REDIS_HOST": "redis-proxy",
                "CELERY_BROKER_URL": "redis://redis-proxy:6379",
                "CELERY_RESULT_BACKEND": "redis://redis-proxy:6379"
            },
            dependencies=["redis"]
        )
        
        # Service API avec proxy
        self.api = ResilientService(
            "api",
            f"lucie-queue/api:{stack_name}",
            self.network,
            environment={
                "REDIS_HOST": "redis-proxy",
                "CELERY_BROKER_URL": "redis://redis-proxy:6379",
                "CELERY_RESULT_BACKEND": "redis://redis-proxy:6379"
            },
            health_check={
                "test": ["CMD", "curl", "-f", "http://localhost:8000/queue/metrics"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 3
            },
            dependencies=["redis", "celery"]
        )

    def export_outputs(self):
        """Exporte les URLs des services."""
        pulumi.export('api_url', "http://localhost:8000")
        pulumi.export('redis_url', "redis://localhost:6379")
        pulumi.export('traefik_dashboard', "http://localhost:8080")

# Création de la stack
stack = ResilientStack(pulumi.get_stack())
stack.export_outputs() 