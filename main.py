import customtkinter as ctk
import requests
import threading
import webbrowser
from tkcalendar import DateEntry

# ==========================================
# API CONFIGURATIONS (Internal Variables)
# ==========================================
FRESH_DOMAIN = ""  # <-- INSERT YOUR DOMAIN HERE (e.g., 'yourcompany')
API_KEY = ""       # <-- INSERT YOUR API KEY HERE

# Global constants
AUTH = (API_KEY, "X")
HEADERS = {"Content-Type": "application/json"}
TIMEOUT = 15

# Color Palette
C_BG = "#0c0c0c"
C_TAB_BG = "#1a1a1a"

C_BLUE = "#1c3553"
C_BLUE_HOVER = "#2a4c75"

C_GREEN = "#1f8b4c"
C_GREEN_HOVER = "#29ab5f"

C_RED = "#9c1c1c"
C_RED_HOVER = "#cf3333"

# ==========================================
# UI SAFE FUNCTIONS & UTILS
# ==========================================
def safe_log(msg, clear=False):
    def _update():
        log_box.configure(state="normal")
        if clear: 
            log_box.delete("0.0", "end")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")
    app.after(0, _update)

def safe_btn_state(btn, state):
    if btn:
        app.after(0, lambda: btn.configure(state=state))

def get_base_url():
    return f"https://{FRESH_DOMAIN}.freshservice.com/api/v2"

# ==========================================
# DATA PARSERS (Nested Dropdown Handlers)
# ==========================================
def parse_dropdown_choices(choices_list, current_path=None):
    """
    Extracts choices into a flat list for UI display, and creates a hidden
    mapping to reconstruct the parent-child hierarchy for the API payload.
    """
    if current_path is None: current_path = []
    display_list = []
    mapping = {}
    
    for c in choices_list:
        if isinstance(c, dict):
            val = str(c.get('value', '')).strip()
            if not val: continue
            
            new_path = current_path + [val]
            display_list.append(val)
            mapping[val] = new_path
            
            nested = c.get('nested_options', [])
            if isinstance(nested, list) and nested:
                sub_disp, sub_map = parse_dropdown_choices(nested, new_path)
                display_list.extend(sub_disp)
                mapping.update(sub_map)
        else:
            val = str(c).strip()
            if not val: continue
            
            new_path = current_path + [val]
            display_list.append(val)
            mapping[val] = new_path
            
    return display_list, mapping

# ==========================================
# CUSTOM WIDGETS (Searchable Combobox)
# ==========================================
class SearchableComboBox(ctk.CTkFrame):
    """
    A custom searchable dropdown that uses a floating Toplevel window for 
    perfect mouse-wheel scrolling and text filtering.
    """
    def __init__(self, master, values, width=480, **kwargs):
        super().__init__(master, width=width, fg_color="transparent", **kwargs)
        self.values = values
        
        self.entry = ctk.CTkEntry(self, width=width, fg_color=C_TAB_BG, border_color=C_GREEN, placeholder_text="Type to search or click to view all...")
        self.entry.pack(fill="x")
        
        self.entry.bind("<KeyRelease>", self.filter_list)
        self.entry.bind("<Button-1>", self.show_list)
        
        self.list_window = None
        self.click_bind_id = None

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        
    def delete(self, first, last=None):
        self.entry.delete(first, last)

    def show_list(self, event=None):
        if self.list_window and self.list_window.winfo_exists():
            return
            
        self.list_window = ctk.CTkToplevel(self)
        self.list_window.overrideredirect(True)
        self.list_window.attributes("-topmost", True)
        
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2
        self.list_window.geometry(f"{self.entry.winfo_width()}x220+{x}+{y}")
        
        self.scroll = ctk.CTkScrollableFrame(self.list_window, fg_color=C_TAB_BG, border_color=C_GREEN, border_width=1)
        self.scroll.pack(fill="both", expand=True)
        
        self.populate(self.values)
        self.click_bind_id = app.bind("<Button-1>", self.check_click_outside, add="+")

    def populate(self, items):
        for w in self.scroll.winfo_children():
            w.destroy()
            
        if not items:
            lbl = ctk.CTkLabel(self.scroll, text="No matches found", text_color="gray")
            lbl.pack(pady=10)
            return
            
        for item in items:
            btn = ctk.CTkButton(self.scroll, text=item, fg_color="transparent", anchor="w", 
                                hover_color=C_BLUE_HOVER, text_color="white",
                                command=lambda v=item: self.select(v))
            btn.pack(fill="x", padx=2, pady=1)

    def filter_list(self, event=None):
        if event and event.keysym in ["Up", "Down", "Left", "Right", "Return", "Tab", "Shift_L", "Shift_R"]:
            return
            
        typed = self.entry.get().lower()
        filtered = [v for v in self.values if typed in v.lower()]
        
        if not self.list_window or not self.list_window.winfo_exists():
            self.show_list()
        else:
            self.populate(filtered)

    def select(self, value):
        self.set(value)
        self.close_list()

    def close_list(self):
        if self.list_window:
            self.list_window.destroy()
            self.list_window = None
            if self.click_bind_id:
                app.unbind("<Button-1>", self.click_bind_id)
                self.click_bind_id = None

    def check_click_outside(self, event):
        if self.list_window and self.list_window.winfo_exists():
            x, y = event.x_root, event.y_root
            wx, wy = self.list_window.winfo_rootx(), self.list_window.winfo_rooty()
            ww, wh = self.list_window.winfo_width(), self.list_window.winfo_height()
            ex, ey = self.entry.winfo_rootx(), self.entry.winfo_rooty()
            ew, eh = self.entry.winfo_width(), self.entry.winfo_height()
            
            in_list = (wx <= x <= wx + ww) and (wy <= y <= wy + wh)
            in_entry = (ex <= x <= ex + ew) and (ey <= y <= ey + eh)
            
            if not (in_list or in_entry):
                self.close_list()

# ==========================================
# CORE API FUNCTIONS
# ==========================================
def fetch_all_objects(log=True):
    url = f"{get_base_url()}/objects"
    all_objects = []
    page = 1
    
    if log: safe_log("Fetching Custom Objects from Freshservice...")
    
    while True:
        try:
            res = requests.get(url, params={"page": page}, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
            if res.status_code == 200:
                data = res.json()
                objects_data = data.get("custom_objects", data.get("objects", []))
                
                if isinstance(objects_data, dict):
                    objects_list = list(objects_data.values())
                elif isinstance(objects_data, list):
                    objects_list = objects_data
                else:
                    objects_list = []
                    
                all_objects.extend(objects_list)
                
                meta = data.get("meta")
                if not meta: break
                
                count = meta.get("count", 0)
                per_page = meta.get("per_page", 30)
                
                if log: safe_log(f" -> Read page {page} ({len(objects_list)} objects)...")
                
                if page * per_page >= count: break
                page += 1
            else:
                if log: safe_log(f"[ERROR] Failed to fetch objects. Status: {res.status_code} - {res.text}")
                break
        except Exception as e:
            if log: safe_log(f"[ERROR] Network error while fetching objects: {e}")
            break
            
    return all_objects

def resolve_object_id(name_or_id):
    if name_or_id.isdigit():
        return name_or_id
        
    objects = fetch_all_objects(log=False)
    for obj in objects:
        if isinstance(obj, dict):
            inner = obj.get("object", obj.get("custom_object", obj))
            obj_name = str(inner.get("name", inner.get("title", "")))
            if obj_name.strip().lower() == name_or_id.strip().lower():
                return str(inner.get("id"))
    return None

# ==========================================
# TAB 1: LIST OBJECTS
# ==========================================
def thread_list_objects(btn):
    safe_btn_state(btn, "disabled")
    safe_log("--- LISTING ALL CUSTOM OBJECTS ---", clear=True)
    
    objects = fetch_all_objects()
    
    if objects:
        safe_log("\n" + "="*50)
        safe_log(f"{'ID'.ljust(15)} | {'NAME'}")
        safe_log("-" * 50)
        for obj in objects:
            if isinstance(obj, dict):
                inner = obj.get("object", obj.get("custom_object", obj))
                o_id = str(inner.get("id", inner.get("display_id", "N/A")))
                o_name = str(inner.get("name", inner.get("title", inner.get("label", "N/A"))))
            else:
                o_id = "N/A"
                o_name = str(obj)
                
            safe_log(f"{o_id.ljust(15)} | {o_name}")
            
        safe_log("="*50 + f"\nTotal: {len(objects)} object(s) found.")
    else:
        safe_log("\nNo objects found or error occurred.")
        
    safe_log("--- PROCESS FINISHED ---")
    safe_btn_state(btn, "normal")

# ==========================================
# TAB 2: VIEW OBJECT (GET)
# ==========================================
def thread_view_object(identifier, btn):
    safe_btn_state(btn, "disabled")
    safe_log(f"--- FETCHING OBJECT: {identifier} ---", clear=True)
    
    if not identifier:
        safe_log("[ERROR] Identifier is required.")
        safe_btn_state(btn, "normal")
        return
        
    obj_id = resolve_object_id(identifier)
    if not obj_id:
        safe_log(f"[ERROR] Could not resolve '{identifier}' to a valid Object ID.")
        safe_btn_state(btn, "normal")
        return
        
    safe_log(f"Resolved ID: {obj_id}. Fetching schema...")
    
    url = f"{get_base_url()}/objects/{obj_id}"
    
    try:
        res = requests.get(url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if res.status_code == 200:
            obj_data = res.json().get("custom_object", res.json().get("object", {}))
            
            safe_log("\n" + "="*60)
            safe_log(f"OBJECT NAME: {obj_data.get('name')} (ID: {obj_data.get('id')})")
            safe_log(f"DESCRIPTION: {obj_data.get('description', 'N/A')}")
            safe_log("="*60)
            
            fields = obj_data.get("fields", [])
            if fields:
                safe_log(f"\n{'FIELD NAME'.ljust(25)} | {'TYPE'.ljust(15)} | {'MANDATORY'}")
                safe_log("-" * 60)
                for f in fields:
                    req = "Yes" if f.get("required") else "No"
                    f_type = f.get('type', 'N/A')
                    safe_log(f"{f.get('name').ljust(25)} | {f_type.ljust(15)} | {req}")
                safe_log("-" * 60)
            else:
                safe_log("No fields defined for this object.")
        else:
            safe_log(f"[ERROR] API returned status {res.status_code}: {res.text}")
    except Exception as e:
        safe_log(f"[ERROR] Network error: {e}")
        
    safe_log("\n--- PROCESS FINISHED ---")
    safe_btn_state(btn, "normal")

# ==========================================
# TAB 3: ADD RECORD
# ==========================================
dynamic_entries = {}
current_object_id_for_record = None

def create_numeric_var():
    var = ctk.StringVar()
    def enforce_numeric(*args):
        val = var.get()
        clean = "".join(c for c in val if c.isdigit() or c in ".-")
        if clean != val:
            var.set(clean)
    var.trace_add("write", enforce_numeric)
    return var

def thread_load_record_form(identifier, btn_load, btn_save):
    safe_btn_state(btn_load, "disabled")
    safe_log(f"--- LOADING FORM FOR: {identifier} ---", clear=True)
    
    if not identifier:
        safe_log("[ERROR] Identifier is required.")
        safe_btn_state(btn_load, "normal")
        return
        
    obj_id = resolve_object_id(identifier)
    if not obj_id:
        safe_log(f"[ERROR] Could not resolve '{identifier}' to a valid Object ID.")
        safe_btn_state(btn_load, "normal")
        return
        
    global current_object_id_for_record
    current_object_id_for_record = obj_id
    
    url = f"{get_base_url()}/objects/{obj_id}"
    
    try:
        res = requests.get(url, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if res.status_code == 200:
            fields = res.json().get("custom_object", res.json().get("object", {})).get("fields", [])
            
            for widget in record_scroll_frame.winfo_children():
                widget.destroy()
            
            dynamic_entries.clear()
            
            if not fields:
                safe_log("[WARNING] This object has no fields.")
            else:
                row_idx = 0
                for f in fields:
                    f_name = f.get('name', 'unknown')
                    f_label = f.get('label', f_name)
                    f_type = str(f.get('type', 'text')).lower()
                    f_req = "*" if f.get('required') else ""
                    
                    if f_type == 'section':
                        lbl = ctk.CTkLabel(record_scroll_frame, text=f_label.upper(), text_color=C_BLUE, font=("Arial", 14, "bold"))
                        lbl.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(20, 5))
                        row_idx += 1
                        continue
                        
                    lbl = ctk.CTkLabel(record_scroll_frame, text=f"{f_label} ({f_type.capitalize()}) {f_req}", text_color="white")
                    lbl.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(10, 0))
                    row_idx += 1
                    
                    if f_type == 'paragraph':
                        ent = ctk.CTkTextbox(record_scroll_frame, width=480, height=80, fg_color=C_TAB_BG, border_color=C_GREEN, border_width=1)
                        ent.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(0, 5))
                        dynamic_entries[f_name] = {"widget": ent, "type": f_type}
                    
                    elif f_type == 'dropdown':
                        raw_choices = f.get('choices', [])
                        
                        is_nested = False
                        for c in raw_choices:
                            if isinstance(c, dict) and c.get('nested_options'):
                                is_nested = True
                                break
                        
                        display_list, mapping = parse_dropdown_choices(raw_choices)
                        if not display_list: display_list = [""]
                        
                        ent = SearchableComboBox(record_scroll_frame, values=display_list, width=480)
                        ent.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(0, 5))
                        dynamic_entries[f_name] = {"widget": ent, "type": f_type, "is_nested": is_nested, "mapping": mapping}
                        
                    elif f_type == 'number':
                        n_var = create_numeric_var()
                        ent = ctk.CTkEntry(record_scroll_frame, width=480, fg_color=C_TAB_BG, border_color=C_GREEN, textvariable=n_var)
                        ent.configure(placeholder_text="Strictly numeric value")
                        ent.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(0, 5))
                        dynamic_entries[f_name] = {"widget": ent, "type": f_type}
                        
                    elif f_type == 'date':
                        cal = DateEntry(record_scroll_frame, width=15, background='#1c3553', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
                        cal.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(0, 5))
                        dynamic_entries[f_name] = {"widget": cal, "type": f_type}
                        
                    elif f_type in ['datetime', 'date_time']:
                        frame_dt = ctk.CTkFrame(record_scroll_frame, fg_color="transparent")
                        frame_dt.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(0, 5))
                        
                        cal = DateEntry(frame_dt, width=15, background='#1c3553', foreground='white', borderwidth=0, date_pattern='yyyy-mm-dd')
                        cal.pack(side="left", padx=(0, 10))
                        
                        time_ent = ctk.CTkEntry(frame_dt, width=100, fg_color=C_TAB_BG, border_color=C_GREEN, placeholder_text="HH:MM:SS")
                        time_ent.pack(side="left")
                        
                        dynamic_entries[f_name] = {"widget": (cal, time_ent), "type": f_type}
                    
                    else:
                        ent = ctk.CTkEntry(record_scroll_frame, width=480, fg_color=C_TAB_BG, border_color=C_GREEN)
                        if f_type == 'lookup':
                            ent.configure(placeholder_text="Enter target ID only (e.g. 1400000123)")
                        ent.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(0, 5))
                        dynamic_entries[f_name] = {"widget": ent, "type": f_type}
                        
                    row_idx += 1
                    
                safe_log(f"[SUCCESS] Form loaded for Object ID: {obj_id}. Please fill the fields and submit.")
                safe_btn_state(btn_save, "normal")
        else:
            safe_log(f"[ERROR] API returned status {res.status_code}: {res.text}")
    except Exception as e:
        safe_log(f"[ERROR] Network error: {e}")

    safe_btn_state(btn_load, "normal")

def thread_save_record(btn):
    safe_btn_state(btn, "disabled")
    safe_log("--- SAVING RECORD ---", clear=False)
    
    data_payload = {}
    
    for f_name, info in dynamic_entries.items():
        w = info["widget"]
        t = info["type"]
        val = None
        
        if t == 'date':
            val = w.get() 
        elif t in ['datetime', 'date_time']:
            cal_w, time_w = w
            date_val = cal_w.get()
            time_val = time_w.get().strip() or "00:00:00"
            
            parts = time_val.split(":")
            if len(parts) == 1: time_val = f"{parts[0]:0>2}:00:00"
            elif len(parts) == 2: time_val = f"{parts[0]:0>2}:{parts[1]:0>2}:00"
            elif len(parts) >= 3: time_val = f"{parts[0]:0>2}:{parts[1]:0>2}:{parts[2]:0>2}"
                
            val = f"{date_val}T{time_val}.000Z"
        elif t == 'paragraph':
            val = w.get("1.0", "end-1c").strip()
        else:
            val = w.get().strip()
            
        if val:
            if t == 'number':
                try: val = float(val) if '.' in val else int(val)
                except ValueError: pass 
                    
            elif t == 'lookup':
                if str(val).isdigit(): val = int(val)
            
            # Submits standard fields or converts flat nested dropdown val into dd1, dd2, etc.
            if t == 'dropdown' and info.get("is_nested"):
                mapping = info.get("mapping", {})
                path = mapping.get(val, [val]) # Fallback is the raw value
                for i, p in enumerate(path):
                    data_payload[f"{f_name}_dd{i+1}"] = p
            else:
                data_payload[f_name] = val
            
    if not data_payload:
        safe_log("[WARNING] No data entered.")
        safe_btn_state(btn, "normal")
        return
        
    payload = {"data": data_payload}
    url = f"{get_base_url()}/objects/{current_object_id_for_record}/records"
    
    try:
        res = requests.post(url, json=payload, auth=AUTH, headers=HEADERS, timeout=TIMEOUT)
        if res.status_code in [200, 201]:
            safe_log(f"[SUCCESS] Record created successfully!")
            
            for info in dynamic_entries.values():
                w = info["widget"]
                if info["type"] == 'paragraph':
                    w.delete("1.0", "end")
                elif info["type"] in ['datetime', 'date_time']:
                    w[1].delete(0, "end") 
                elif info["type"] == 'dropdown':
                    w.set("")
                elif info["type"] != 'date':
                    w.delete(0, "end")
        else:
            safe_log(f"[ERROR] Failed to save record. Status: {res.status_code}\nDetails: {res.text}")
    except Exception as e:
        safe_log(f"[ERROR] Network error: {e}")
        
    safe_log("--- PROCESS FINISHED ---")
    safe_btn_state(btn, "normal")

# ==========================================
# GRAPHICAL INTERFACE (GUI)
# ==========================================
app = ctk.CTk()
app.title("Freshservice Custom Object Manager")
app.geometry("650x850")
app.configure(fg_color=C_BG)

# Header Frame
header_frame = ctk.CTkFrame(app, fg_color="transparent")
header_frame.pack(fill="x", padx=20, pady=(15, 10))

title_lbl = ctk.CTkLabel(header_frame, text="Freshservice Custom Object Manager", font=("Arial", 22, "bold"), text_color="white")
title_lbl.grid(row=0, column=0, sticky="w")

# Tabview
main_tabview = ctk.CTkTabview(app, width=610, height=450, fg_color=C_TAB_BG, 
                              segmented_button_selected_color=C_BLUE, 
                              segmented_button_selected_hover_color=C_BLUE_HOVER)
main_tabview.pack(padx=20, pady=(0, 10))

tab_list = main_tabview.add("List Objects")
tab_view = main_tabview.add("View Object")
tab_record = main_tabview.add("Add Record")

def on_tab_change():
    t = main_tabview.get()
    color = C_BLUE if t == "List Objects" else C_GREEN if t == "View Object" else C_RED
    hover = C_BLUE_HOVER if t == "List Objects" else C_GREEN_HOVER if t == "View Object" else C_RED_HOVER
    main_tabview.configure(segmented_button_selected_color=color, segmented_button_selected_hover_color=hover)

main_tabview.configure(command=on_tab_change)

# --- TAB: LIST OBJECTS ---
ctk.CTkLabel(tab_list, text="Fetch and list all Custom Objects in the environment.", text_color="gray").pack(pady=(30, 20))
btn_list = ctk.CTkButton(tab_list, text="Fetch Objects", fg_color=C_BLUE, hover_color=C_BLUE_HOVER,
                         command=lambda: threading.Thread(target=thread_list_objects, args=(btn_list,)).start())
btn_list.pack()

# --- TAB: VIEW OBJECT ---
ctk.CTkLabel(tab_view, text="Object Name or ID:", text_color="white").pack(anchor="w", padx=10, pady=(30, 0))
entry_v_ident = ctk.CTkEntry(tab_view, width=550, fg_color=C_BG, border_color=C_GREEN)
entry_v_ident.pack(padx=10, pady=(0, 20))

btn_view = ctk.CTkButton(tab_view, text="Inspect Object Schema", fg_color=C_GREEN, hover_color=C_GREEN_HOVER,
                         command=lambda: threading.Thread(target=thread_view_object, args=(entry_v_ident.get(), btn_view)).start())
btn_view.pack()

# --- TAB: ADD RECORD ---
frame_rec_top = ctk.CTkFrame(tab_record, fg_color="transparent")
frame_rec_top.pack(fill="x", padx=10, pady=10)

ctk.CTkLabel(frame_rec_top, text="Object Name/ID:", text_color="white").pack(side="left")
entry_r_ident = ctk.CTkEntry(frame_rec_top, width=250, fg_color=C_BG, border_color=C_RED)
entry_r_ident.pack(side="left", padx=10)

btn_load_form = ctk.CTkButton(frame_rec_top, text="Load Form", width=100, fg_color=C_RED, hover_color=C_RED_HOVER,
                              command=lambda: threading.Thread(target=thread_load_record_form, args=(entry_r_ident.get(), btn_load_form, btn_save_rec)).start())
btn_load_form.pack(side="left")

# Scrollable Frame for dynamic form
record_scroll_frame = ctk.CTkScrollableFrame(tab_record, width=550, height=250, fg_color="#141414")
record_scroll_frame.pack(padx=10, pady=(5, 10), fill="both", expand=True)

btn_save_rec = ctk.CTkButton(tab_record, text="Submit Record", fg_color=C_RED, hover_color=C_RED_HOVER, state="disabled",
                             command=lambda: threading.Thread(target=thread_save_record, args=(btn_save_rec,)).start())
btn_save_rec.pack(pady=(0, 10))

# --- GENERAL LOG BOX ---
log_box = ctk.CTkTextbox(app, width=610, height=220, fg_color=C_TAB_BG, border_color="#333333", border_width=1, text_color="white", font=("Consolas", 12))
log_box.pack(padx=20, pady=(5, 10))
log_box.insert("0.0", "Welcome to Freshservice Custom Object Manager.\nPlease enter your API credentials in the script to begin.\n")
log_box.configure(state="disabled")

# --- HYPERLINK ---
link_font = ctk.CTkFont(family="Arial", size=11, underline=True)
doc_link = ctk.CTkLabel(app, text="Freshservice API Docs", text_color="#1c94e0", font=link_font, cursor="hand2")
doc_link.place(relx=0.98, rely=0.99, anchor="se")
doc_link.bind("<Button-1>", lambda e: webbrowser.open("https://api.freshservice.com/"))

app.mainloop()