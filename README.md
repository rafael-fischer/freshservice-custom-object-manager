## Prerequisites

Before running the application, ensure you have Python 3.x installed. It is highly recommended to use a virtual environment.

Install all the required dependencies at once using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Configuration

Open the main script and fill in your environment properties at the top of the file:

```python
FRESH_DOMAIN = "your-company-subdomain"  # Do not include '.freshservice.com'
API_KEY = "your-freshservice-api-key"
```

*Note: Never commit your raw API keys to public repositories. Ensure these fields are cleared before publishing.*

## Usage

Run the script from your terminal:

```bash
python main.py
```