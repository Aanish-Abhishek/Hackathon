import json
import os
import threading
import urllib.error
import urllib.request
import uuid
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog

# ---------------------------------------------------------
# Color palette
# ---------------------------------------------------------

COLOR_BACKGROUND = "#F3F6FA"
COLOR_CARD = "#FFFFFF"
COLOR_PRIMARY = "#0067B8"
COLOR_PRIMARY_DARK = "#005A9E"
COLOR_TEXT = "#1F2937"
COLOR_MUTED = "#667085"
COLOR_BORDER = "#D0D5DD"
COLOR_DANGER = "#B42318"
COLOR_DANGER_BACKGROUND = "#FEE4E2"
COLOR_SUCCESS = "#067647"
COLOR_SUCCESS_BACKGROUND = "#DCFAE6"
COLOR_WARNING = "#B54708"
COLOR_WARNING_BACKGROUND = "#FEF0C7"
BACKEND_ANALYZE_URL = os.getenv(
    "TRACEFIX_BACKEND_URL",
    "http://127.0.0.1:8000/analyze-logs"
)


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def set_text(widget, content):
    """
    Safely update a read-only Text widget.
    """

    widget.config(state="normal")
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, content)
    widget.config(state="disabled")


def update_status(message, color=COLOR_MUTED):
    """
    Update the status message displayed at the bottom.
    """

    status_label.config(
        text=message,
        fg=color
    )


def clear_results():
    """
    Reset all investigation result controls.
    """

    classification_value.config(text="Not analyzed")
    priority_value.config(text="--")
    severity_value.config(text="--")
    confidence_value.config(text="--")

    set_text(
        overview_text,
        "Investigation results will appear here after analysis."
    )

    set_text(
        evidence_text,
        "Matched log evidence will appear here."
    )

    set_text(
        actions_text,
        "Investigation and recovery steps will appear here."
    )

    update_status("Ready for incident analysis.")


def clear_form():
    """
    Clear incident details, logs, and existing results.
    """

    incident_text.delete("1.0", tk.END)
    log_text.delete("1.0", tk.END)
    selected_file_label.config(
        text="No log file selected",
        fg=COLOR_MUTED
    )

    clear_results()

    update_status("Form cleared.")


def upload_log_file():
    """
    Allow the user to select a production log file.
    """

    file_path = filedialog.askopenfilename(
        title="Select Production Log",
        filetypes=[
            ("Log files", "*.log"),
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
    )

    if not file_path:
        return

    try:
        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as log_file:
            content = log_file.read()

        log_text.delete("1.0", tk.END)
        log_text.insert(tk.END, content)

        selected_file_label.config(
            text=file_path,
            fg=COLOR_SUCCESS
        )

        update_status(
            "Production log loaded successfully.",
            COLOR_SUCCESS
        )

    except Exception as error:
        messagebox.showerror(
            "Log Upload Error",
            f"Unable to read the selected log file.\n\n{error}"
        )


def get_priority(severity):
    """
    Convert incident severity into operational priority.
    """

    priority_mapping = {
        "Critical": "P1",
        "High": "P2",
        "Medium": "P3",
        "Low": "P4"
    }

    return priority_mapping.get(severity, "P3")


def apply_severity_style(severity):
    """
    Apply a color style to the severity result.
    """

    if severity == "Critical":
        severity_value.config(
            fg=COLOR_DANGER,
            bg=COLOR_DANGER_BACKGROUND
        )

    elif severity == "High":
        severity_value.config(
            fg=COLOR_WARNING,
            bg=COLOR_WARNING_BACKGROUND
        )

    else:
        severity_value.config(
            fg=COLOR_SUCCESS,
            bg=COLOR_SUCCESS_BACKGROUND
        )


def analyze_incident():
    """
    Submit the production log to the FastAPI repository analyzer.
    """

    application_name = app_combo.get().strip()
    environment_name = env_combo.get().strip()

    incident_details = incident_text.get(
        "1.0",
        tk.END
    ).strip()

    logs = log_text.get(
        "1.0",
        tk.END
    ).strip()

    if not application_name:
        messagebox.showwarning(
            "Missing Application",
            "Please select an application."
        )
        return

    if not environment_name:
        messagebox.showwarning(
            "Missing Environment",
            "Please select an environment."
        )
        return

    if not incident_details:
        messagebox.showwarning(
            "Missing Incident Details",
            "Please enter a brief incident description."
        )
        return

    if not logs:
        messagebox.showwarning(
            "Missing Production Log",
            "Please paste or upload a production log before analysis."
        )
        return

    filename = os.path.basename(selected_file_label.cget("text"))
    if not filename or filename == "No log file selected":
        filename = "pasted-log.txt"

    analyze_button.config(
        text="Analyzing...",
        state="disabled"
    )

    progress_bar.start(10)

    update_status(
        "TraceFix AI is investigating the log and repository...",
        COLOR_PRIMARY
    )

    worker = threading.Thread(
        target=submit_analysis,
        args=(logs, filename, application_name, environment_name, incident_details),
        daemon=True
    )
    worker.start()


def submit_analysis(logs, filename, application_name, environment_name, incident_details):
    """Send the log to the API away from Tk's event loop."""

    try:
        boundary = uuid.uuid4().hex
        body = b"".join([
            f"--{boundary}\r\n".encode("ascii"),
            (
                f'Content-Disposition: form-data; name="files"; '
                f'filename="{filename.replace(chr(34), "")}"\r\n'
                "Content-Type: text/plain; charset=utf-8\r\n\r\n"
            ).encode("utf-8"),
            logs.encode("utf-8"),
            b"\r\n",
        ])
        for field_name, field_value in (
            ("application_name", application_name),
            ("environment_name", environment_name),
            ("incident_details", incident_details),
        ):
            body += (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'
                f"{field_value}\r\n"
            ).encode("utf-8")
        body += f"--{boundary}--\r\n".encode("ascii")
        request = urllib.request.Request(
            BACKEND_ANALYZE_URL,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8")).get(
                    "detail",
                    str(error)
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = str(error)
            raise RuntimeError(f"Backend returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Unable to connect to the analysis backend at "
                f"{BACKEND_ANALYZE_URL}. Start the FastAPI service and try again."
            ) from error

        root.after(
            0,
            lambda: display_analysis_result(
                result,
                application_name,
                environment_name,
                incident_details
            )
        )
    except Exception as error:
        root.after(0, lambda error=error: show_analysis_error(error))


def display_analysis_result(result, application_name, environment_name, incident_details):
    """Render the API's structured findings in the existing results view."""

    progress_bar.stop()
    analyze_button.config(text="Analyze Incident", state="normal")

    findings = result.get("findings", [])
    classification_value.config(
        text=result.get("summary") or f"Repository analysis: {len(findings)} finding(s)"
    )

    if not findings:
        priority_value.config(text="--")
        severity_value.config(text="--")
        confidence_value.config(text="--")
        set_text(
            overview_text,
            f"APPLICATION\n{application_name}\n\n"
            f"ENVIRONMENT\n{environment_name}\n\n"
            f"INCIDENT DETAILS\n{incident_details}\n\n"
            "No potential root causes were returned for the supplied logs "
            "and repository."
        )
        set_text(evidence_text, "No log or repository evidence was returned.")
        set_text(actions_text, "No suggested fixes were returned.")
    else:
        first = findings[0]
        severity = first.get("severity", "Unknown")
        priority_value.config(text=get_priority(severity))
        severity_value.config(text=severity)
        confidence_value.config(
            text=f"{round(first.get('confidence', 0) * 100)}%"
        )
        apply_severity_style(severity)

        overview_sections = [
            f"APPLICATION\n{application_name}",
            f"ENVIRONMENT\n{environment_name}",
            f"INCIDENT DETAILS\n{incident_details}",
            f"ANALYSIS MODE\n{result.get('analysis_mode', 'unknown')}",
            f"ANALYZED REPOSITORY FILES\n"
            f"{', '.join(result.get('repository_files', [])) or 'None'}"
        ]
        for index, finding in enumerate(findings, start=1):
            overview_sections.append(
                f"FINDING {index}: {finding.get('error_type', 'Error')}\n"
                f"Severity: {finding.get('severity', 'Unknown')}\n"
                f"Location: {finding.get('file', 'Unknown')} — "
                f"{finding.get('function', 'Unknown')}\n"
                f"Suspected root cause: "
                f"{finding.get('suspected_root_cause', 'Unavailable')}\n"
                f"Suggested fix: {finding.get('suggested_fix', 'Unavailable')}"
            )

        evidence_sections = []
        action_sections = []
        for index, finding in enumerate(findings, start=1):
            evidence = finding.get("evidence", [])
            evidence_sections.append(
                f"FINDING {index}: {finding.get('error_type', 'Error')}\n"
                + ("\n".join(f"• {item}" for item in evidence)
                   if evidence else "No supporting evidence supplied.")
            )
            action_sections.append(
                f"FINDING {index}: {finding.get('file', 'Unknown')} — "
                f"{finding.get('function', 'Unknown')}\n"
                f"{finding.get('suggested_fix', 'No fix supplied.')}"
            )

        set_text(overview_text, "\n\n".join(overview_sections))
        set_text(evidence_text, "\n\n".join(evidence_sections))
        set_text(actions_text, "\n\n".join(action_sections))

    result_notebook.select(overview_tab)
    update_status(
        f"Analysis completed: {len(findings)} finding(s).",
        COLOR_SUCCESS
    )


def show_analysis_error(error):
    """Restore the UI and report backend/provider failures explicitly."""

    progress_bar.stop()
    analyze_button.config(text="Analyze Incident", state="normal")
    update_status("Incident analysis failed.", COLOR_DANGER)
    messagebox.showerror(
        "Analysis Error",
        f"TraceFix AI could not analyze the incident.\n\n{error}"
    )


# ---------------------------------------------------------
# Main window
# ---------------------------------------------------------

root = tk.Tk()

root.title("TraceFix AI")
root.geometry("1280x820")
root.minsize(1000, 680)
root.configure(bg=COLOR_BACKGROUND)

try:
    root.state("zoomed")
except tk.TclError:
    pass


# ---------------------------------------------------------
# ttk styles
# ---------------------------------------------------------

style = ttk.Style()

try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure(
    "TCombobox",
    padding=7
)

style.configure(
    "TNotebook",
    background=COLOR_CARD,
    borderwidth=0
)

style.configure(
    "TNotebook.Tab",
    padding=(18, 9),
    font=("Segoe UI", 10, "bold")
)

style.map(
    "TNotebook.Tab",
    background=[
        ("selected", COLOR_PRIMARY)
    ],
    foreground=[
        ("selected", "white")
    ]
)

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

header_frame = tk.Frame(
    root,
    bg=COLOR_PRIMARY,
    height=90
)
header_frame.pack(fill="x")
header_frame.pack_propagate(False)

header_content = tk.Frame(
    header_frame,
    bg=COLOR_PRIMARY
)
header_content.pack(
    fill="both",
    expand=True,
    padx=28
)

tk.Label(
    header_content,
    text="TraceFix AI",
    font=("Segoe UI", 24, "bold"),
    bg=COLOR_PRIMARY,
    fg="white"
).pack(
    anchor="w",
    pady=(14, 0)
)

tk.Label(
    header_content,
    text="AI Production Investigation and Recovery Copilot",
    font=("Segoe UI", 11),
    bg=COLOR_PRIMARY,
    fg="#DCEBFA"
).pack(anchor="w")


# ---------------------------------------------------------
# Main content
# ---------------------------------------------------------

main_content = tk.Frame(
    root,
    bg=COLOR_BACKGROUND
)
main_content.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=18
)

main_content.grid_columnconfigure(0, weight=4)
main_content.grid_columnconfigure(1, weight=6)
main_content.grid_rowconfigure(0, weight=1)


# ---------------------------------------------------------
# Left input card
# ---------------------------------------------------------

input_card = tk.Frame(
    main_content,
    bg=COLOR_CARD,
    highlightbackground=COLOR_BORDER,
    highlightthickness=1
)
input_card.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0, 10)
)

tk.Label(
    input_card,
    text="Incident Input",
    font=("Segoe UI", 15, "bold"),
    bg=COLOR_CARD,
    fg=COLOR_TEXT
).pack(
    anchor="w",
    padx=20,
    pady=(18, 4)
)

tk.Label(
    input_card,
    text="Provide the production context and sanitized log evidence.",
    font=("Segoe UI", 9),
    bg=COLOR_CARD,
    fg=COLOR_MUTED
).pack(
    anchor="w",
    padx=20,
    pady=(0, 15)
)

tk.Label(
    input_card,
    text="Application",
    font=("Segoe UI", 10, "bold"),
    bg=COLOR_CARD,
    fg=COLOR_TEXT
).pack(
    anchor="w",
    padx=20
)

app_combo = ttk.Combobox(
    input_card,
    values=["XONE"],
    state="readonly"
)
app_combo.pack(
    fill="x",
    padx=20,
    pady=(5, 12)
)
app_combo.current(0)

tk.Label(
    input_card,
    text="Environment",
    font=("Segoe UI", 10, "bold"),
    bg=COLOR_CARD,
    fg=COLOR_TEXT
).pack(
    anchor="w",
    padx=20
)

env_combo = ttk.Combobox(
    input_card,
    values=["DEV", "UAT", "PROD"],
    state="readonly"
)
env_combo.pack(
    fill="x",
    padx=20,
    pady=(5, 12)
)
env_combo.current(1)

tk.Label(
    input_card,
    text="Incident Details",
    font=("Segoe UI", 10, "bold"),
    bg=COLOR_CARD,
    fg=COLOR_TEXT
).pack(
    anchor="w",
    padx=20
)

incident_text = tk.Text(
    input_card,
    height=3,
    wrap="word",
    font=("Segoe UI", 10),
    relief="solid",
    borderwidth=1,
    padx=8,
    pady=8
)
incident_text.pack(
    fill="x",
    padx=20,
    pady=(5, 12)
)

tk.Label(
    input_card,
    text="Production Log",
    font=("Segoe UI", 10, "bold"),
    bg=COLOR_CARD,
    fg=COLOR_TEXT
).pack(
    anchor="w",
    padx=20
)

log_text = tk.Text(
    input_card,
    height=8,
    wrap="word",
    font=("Consolas", 9),
    relief="solid",
    borderwidth=1,
    padx=8,
    pady=8
)
log_text.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=(5, 5)
)


# ---------------------------------------------------------
# File buttons
# ---------------------------------------------------------

file_actions_frame = tk.Frame(
    input_card,
    bg=COLOR_CARD
)
file_actions_frame.pack(
    fill="x",
    padx=20
)

upload_button = tk.Button(
    file_actions_frame,
    text="Upload Log",
    command=upload_log_file,
    bg="#E8F1FB",
    fg=COLOR_PRIMARY_DARK,
    activebackground="#D8E9F8",
    font=("Segoe UI", 9, "bold"),
    relief="flat",
    padx=14,
    pady=7,
    cursor="hand2"
)
upload_button.pack(side="left")

clear_button = tk.Button(
    file_actions_frame,
    text="Clear",
    command=clear_form,
    bg="#F2F4F7",
    fg=COLOR_TEXT,
    activebackground="#E4E7EC",
    font=("Segoe UI", 9, "bold"),
    relief="flat",
    padx=14,
    pady=7,
    cursor="hand2"
)
clear_button.pack(
    side="left",
    padx=(8, 0)
)

selected_file_label = tk.Label(
    input_card,
    text="No log file selected",
    font=("Segoe UI", 8),
    bg=COLOR_CARD,
    fg=COLOR_MUTED,
    anchor="w"
)
selected_file_label.pack(
    fill="x",
    padx=20,
    pady=(4, 5)
)


# ---------------------------------------------------------
# Sanitization warning
# ---------------------------------------------------------

warning_label = tk.Label(
    input_card,
    text=(
        "Sanitization required: Remove passwords, tokens, "
        "personal information, and account data."
    ),
    font=("Segoe UI", 8, "bold"),
    bg=COLOR_DANGER_BACKGROUND,
    fg=COLOR_DANGER,
    justify="left",
    wraplength=420,
    padx=8,
    pady=6
)

warning_label.pack(
    fill="x",
    padx=20,
    pady=(0, 8)
)

# ---------------------------------------------------------
# Analyze button and progress bar
# ---------------------------------------------------------

analyze_button = tk.Button(
    input_card,
    text="Analyze Incident",
    command=analyze_incident,
    bg=COLOR_PRIMARY,
    fg="white",
    activebackground=COLOR_PRIMARY_DARK,
    activeforeground="white",
    font=("Segoe UI", 11, "bold"),
    relief="flat",
    padx=20,
    pady=10,
    cursor="hand2"
)
analyze_button.pack(
    fill="x",
    padx=20
)

progress_bar = ttk.Progressbar(
    input_card,
    mode="indeterminate"
)
progress_bar.pack(
    fill="x",
    padx=20,
    pady=(6, 10)
)


# ---------------------------------------------------------
# Right results card
# ---------------------------------------------------------

result_card = tk.Frame(
    main_content,
    bg=COLOR_CARD,
    highlightbackground=COLOR_BORDER,
    highlightthickness=1
)
result_card.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=(10, 0)
)

tk.Label(
    result_card,
    text="Investigation Result",
    font=("Segoe UI", 15, "bold"),
    bg=COLOR_CARD,
    fg=COLOR_TEXT
).pack(
    anchor="w",
    padx=20,
    pady=(18, 4)
)

classification_value = tk.Label(
    result_card,
    text="Not analyzed",
    font=("Segoe UI", 11),
    bg=COLOR_CARD,
    fg=COLOR_MUTED,
    anchor="w",
    justify="left",
    wraplength=650
)
classification_value.pack(
    fill="x",
    padx=20,
    pady=(0, 14)
)


# ---------------------------------------------------------
# Result summary cards
# ---------------------------------------------------------

summary_frame = tk.Frame(
    result_card,
    bg=COLOR_CARD
)
summary_frame.pack(
    fill="x",
    padx=20,
    pady=(0, 14)
)

for column in range(3):
    summary_frame.grid_columnconfigure(column, weight=1)

priority_card = tk.Frame(
    summary_frame,
    bg="#EFF8FF",
    padx=12,
    pady=10
)
priority_card.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=(0, 6)
)

tk.Label(
    priority_card,
    text="Priority",
    font=("Segoe UI", 8),
    bg="#EFF8FF",
    fg=COLOR_MUTED
).pack()

priority_value = tk.Label(
    priority_card,
    text="--",
    font=("Segoe UI", 16, "bold"),
    bg="#EFF8FF",
    fg=COLOR_PRIMARY
)
priority_value.pack()

severity_card = tk.Frame(
    summary_frame,
    bg=COLOR_DANGER_BACKGROUND,
    padx=12,
    pady=10
)
severity_card.grid(
    row=0,
    column=1,
    sticky="ew",
    padx=6
)

tk.Label(
    severity_card,
    text="Severity",
    font=("Segoe UI", 8),
    bg=COLOR_DANGER_BACKGROUND,
    fg=COLOR_MUTED
).pack()

severity_value = tk.Label(
    severity_card,
    text="--",
    font=("Segoe UI", 16, "bold"),
    bg=COLOR_DANGER_BACKGROUND,
    fg=COLOR_DANGER
)
severity_value.pack()

confidence_card = tk.Frame(
    summary_frame,
    bg=COLOR_SUCCESS_BACKGROUND,
    padx=12,
    pady=10
)
confidence_card.grid(
    row=0,
    column=2,
    sticky="ew",
    padx=(6, 0)
)

tk.Label(
    confidence_card,
    text="Confidence",
    font=("Segoe UI", 8),
    bg=COLOR_SUCCESS_BACKGROUND,
    fg=COLOR_MUTED
).pack()

confidence_value = tk.Label(
    confidence_card,
    text="--",
    font=("Segoe UI", 16, "bold"),
    bg=COLOR_SUCCESS_BACKGROUND,
    fg=COLOR_SUCCESS
)
confidence_value.pack()


# ---------------------------------------------------------
# Result tabs
# ---------------------------------------------------------

result_notebook = ttk.Notebook(result_card)
result_notebook.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=(0, 16)
)

overview_tab = tk.Frame(
    result_notebook,
    bg=COLOR_CARD
)

evidence_tab = tk.Frame(
    result_notebook,
    bg=COLOR_CARD
)

actions_tab = tk.Frame(
    result_notebook,
    bg=COLOR_CARD
)

result_notebook.add(
    overview_tab,
    text="Overview"
)

result_notebook.add(
    evidence_tab,
    text="Evidence"
)

result_notebook.add(
    actions_tab,
    text="Actions & Experts"
)


def create_result_text(parent):
    result_container = tk.Frame(
        parent,
        bg=COLOR_CARD
    )
    result_container.pack(
        fill="both",
        expand=True
    )

    scrollbar = tk.Scrollbar(result_container)
    scrollbar.pack(
        side="right",
        fill="y"
    )

    text_widget = tk.Text(
        result_container,
        wrap="word",
        font=("Segoe UI", 10),
        bg=COLOR_CARD,
        fg=COLOR_TEXT,
        relief="flat",
        padx=14,
        pady=14,
        state="disabled",
        yscrollcommand=scrollbar.set
    )
    text_widget.pack(
        side="left",
        fill="both",
        expand=True
    )

    scrollbar.config(command=text_widget.yview)

    return text_widget


overview_text = create_result_text(overview_tab)
evidence_text = create_result_text(evidence_tab)
actions_text = create_result_text(actions_tab)


# ---------------------------------------------------------
# Status bar
# ---------------------------------------------------------

status_frame = tk.Frame(
    root,
    bg="#EAECF0",
    height=30
)
status_frame.pack(
    fill="x",
    side="bottom"
)

status_label = tk.Label(
    status_frame,
    text="Ready for incident analysis.",
    font=("Segoe UI", 9),
    bg="#EAECF0",
    fg=COLOR_MUTED
)
status_label.pack(
    anchor="w",
    padx=20,
    pady=6
)


# ---------------------------------------------------------
# Initial state and application start
# ---------------------------------------------------------

clear_results()

root.mainloop()