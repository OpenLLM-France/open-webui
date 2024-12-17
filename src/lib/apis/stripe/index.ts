// Imports
import { WEBUI_BASE_URL } from "$lib/constants";

export const getSubscriptionInfo = async () => {
    try {
        // API call
        const response = await fetch(`${WEBUI_BASE_URL}/stripe/subscription_info`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(JSON.stringify(errorData));
        }

        // Parse JSON and return data
        return await response.json();
    } catch (error) {
        console.error('Error fetching data:', error);
        return null;
    }
};