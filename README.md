# Minbar - Social Media Ingester

This microservice ingests Facebook data from the Data365 API based on keywords obtained from the Keyword Manager service and stores the raw data.

## API Endpoints

---

### Status Endpoints

#### `GET /`
-   **Description**: Retrieves a welcome message indicating the service is running.
-   **Sample Request**:
    ```http
    GET /
    ```

#### `GET /health`
-   **Description**: Provides a basic health check for the service.
-   **Sample Request**:
    ```http
    GET /health
    ```

---

### Actions

#### `POST /trigger-ingestion`
-   **Description**: Manually triggers one background ingestion cycle. This cycle will fetch keywords, query Data365 for Facebook posts related to those keywords (and modified with a location specifier, e.g., "Tunisia"), and store the retrieved data. The API call returns immediately with a 202 Accepted status, and the ingestion process runs in the background.
    *Note: Be mindful of Data365 API credit limits when using this endpoint, especially during testing.*
-   **Request Body**: None
-   **Sample Request**:
    ```http
    POST /trigger-ingestion
    ```

---