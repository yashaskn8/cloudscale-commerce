from locust import HttpUser, between, task


class CloudScaleUser(HttpUser):
    """Simulates a concurrent user on the CloudScale Commerce platform."""

    wait_time = between(1, 3)

    def on_start(self):
        """Pre-login or initialization if needed."""
        self.token = None
        self.product_id = "3d1d122b-a94b-47cd-899a-aeaae0056325"

    @task(3)
    def browse_products(self):
        """Simulates product listing browse."""
        with self.client.get("/api/v1/products?page=1&size=10", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    items = response.json().get("items", [])
                    if items:
                        # Extract an active product ID for downstream tasks
                        self.product_id = items[0]["id"]
                except ValueError:
                    response.failure("Response was not JSON")

    @task(2)
    def get_product_detail(self):
        """Simulates viewing a single product details (Hit/Miss cache test)."""
        self.client.get(f"/api/v1/products/{self.product_id}")

    @task(1)
    def check_inventory(self):
        """Checks inventory levels."""
        self.client.get("/api/v1/inventory")

    @task(1)
    def submit_order(self):
        """Simulates submitting an order checkout request."""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        payload = {"items": [{"product_id": str(self.product_id), "quantity": 1}]}
        self.client.post("/api/v1/orders", json=payload, headers=headers)
