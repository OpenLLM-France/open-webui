import pytest
import logging

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_api_connectivity(queue_test_helper, test_logger):
    """Test la connectivité de base de l'API."""
    test_logger.info("Début du test de connectivité API")
    
    # Test de tous les endpoints
    results = await queue_test_helper.test_endpoints()
    
    # Analyse des résultats
    for result in results:
        if "error" in result:
            test_logger.error(f"Erreur pour {result['method']} {result['endpoint']}: {result['error']}")
        else:
            test_logger.info(f"Endpoint {result['method']} {result['endpoint']}: status={result['status']}")
            
        # Vérification du statut
        if "status" in result:
            assert result["status"] in [200, 201], f"L'endpoint {result['endpoint']} a retourné un statut {result['status']}"
            
    test_logger.info("Fin du test de connectivité API") 