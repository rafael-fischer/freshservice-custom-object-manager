# Freshservice Custom Object Manager

A Python-based desktop application designed to streamline the management of Custom Object records within Freshservice. It eliminates the hassle of navigating complex API payloads by dynamically rendering user-friendly forms based on your Freshservice Object configuration schemas.

*Note: While built out-of-the-box for the Freshservice v2 API, the underlying engine—which parses JSON schemas to dynamically generate UI components—is highly scalable and can be adapted to other platforms that utilize custom entity schemas.*

This tool bridges the gap between raw API interactions and end-user operations, automatically translating complex nested dropdowns, enforcing strict data types, and ensuring dates are formatted flawlessly before ever hitting the endpoint.

## 🚀 Features

* **Dynamic Form Generation:** Automatically loads and renders appropriate UI input components (Paragraphs, Dates, Lookups, Numbers, etc.) according to the exact field types defined in the Freshservice schema.
* **Smart Searchable Dropdowns:** Implements a custom, high-performance searchable combo widget to dynamically filter huge lists or deeply nested hierarchical dropdown definitions (e.g., parsing `Parent > Child` structures into proper API tokens).
* **Strict Data Validation:** Automatically forces number-only inputs where required and normalizes human-entered dates into rigorous API-ready ISO formats (`YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS.000Z`) using embedded calendar widgets.
* **Schema Inspection:** Decodes and prints target object structures into a human-readable tabular log inside the application, showing field types and mandatory constraints.
* **Object Enumeration:** Automatically fetches and lists all custom objects in your environment, utilizing precise pagination parsing (`meta` tokens).

## 🛠️ How It Works

The workflow is designed to be completed in a few simple steps:
1. **Configure Credentials:** The user inserts their Freshservice Domain and API Key directly into the configuration block of the script.
2. **List & Inspect (Optional):** The user can fetch all Custom Objects to grab their specific IDs or inspect their exact JSON schema directly in the UI log.
3. **Load Form:** By providing an Object ID, the application hits the API, parses the schema, and instantly builds a customized UI form matching the required fields.
4. **Submit Record:** The user fills out the generated fields. The app automatically cleans the data, maps nested dropdowns to the correct keys (`_dd1`, `_dd2`), formats dates, and sends the payload back to Freshservice to create the record.

## 💻 Prerequisites & Installation

To run this application locally, ensure you have Python 3.x installed. It is highly recommended to use a virtual environment.

1. Clone this repository:
```bash
git clone [https://github.com/yourusername/freshservice-custom-object-manager.git](https://github.com/yourusername/freshservice-custom-object-manager.git)
```

2. Navigate to the project directory:
```bash
cd freshservice-custom-object-manager
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## 📂 Project Structure

* `main.py`: The main application script containing the CustomTkinter UI, the custom widget classes, and the dynamic API request logic.
* `requirements.txt`: The list of Python library dependencies required to run the tool.

## 📦 Dependencies

* `customtkinter` - For the modern, dark-mode graphical user interface.
* `requests` - For handling REST API GET and POST requests to the Freshservice endpoints.
* `tkcalendar` - For native, interactive date and datetime picker widgets.
