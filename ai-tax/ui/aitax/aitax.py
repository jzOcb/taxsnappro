"""
TaxSnapPro - Main Application (Fintech Light Theme)
"""
import reflex as rx
from .state import TaxAppState
from .components import (
    COLORS, fintech_card, mercury_card, gradient_button, outline_button, stat_card,
    section_header, empty_state, badge, data_row, document_card,
    nav_bar, page_container, api_key_modal, processing_overlay,
)


# ============== Styled Input Helper ==============
def styled_input(placeholder: str, value, on_change, input_type: str = "text", width: str = "100%") -> rx.Component:
    """Styled input with fintech theme."""
    return rx.input(
        placeholder=placeholder,
        value=value,
        on_change=on_change,
        type=input_type,
        width=width,
        background="white",
        border=f"1px solid {COLORS['border']}",
        color=COLORS["text_primary"],
        _placeholder={"color": COLORS["text_muted"]},
        padding="10px 12px",
        border_radius="8px",
        _focus={
            "border_color": COLORS["accent_primary"], 
            "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"
        },
    )


# ============== Upload Zone (Compact) ==============
def upload_zone_compact() -> rx.Component:
    """Compact file upload dropzone."""
    return rx.upload(
        rx.hstack(
            rx.box(
                rx.icon("upload", size=24, color=COLORS["accent_primary"]),
                background=COLORS["accent_light"],
                padding="12px",
                border_radius="8px",
            ),
            rx.vstack(
                rx.text("Drop files here or click to browse", color=COLORS["text_primary"], 
                        font_size="15px", font_weight="500"),
                rx.text("W-2, 1099, 1098 (PNG/JPG)", 
                        color=COLORS["text_muted"], font_size="13px"),
                align_items="start",
                spacing="0",
            ),
            rx.spacer(),
            rx.box(
                rx.text("Browse", font_size="14px"),
                background=f"linear-gradient(135deg, {COLORS['accent_primary']} 0%, {COLORS['accent_purple']} 100%)",
                color="white",
                padding="8px 16px",
                border_radius="6px",
                font_weight="500",
            ),
            spacing="4",
            padding="20px 24px",
            width="100%",
            align_items="center",
        ),
        id="upload",
        border=f"2px dashed {COLORS['border']}",
        border_radius="12px",
        background="white",
        _hover={
            "border_color": COLORS["accent_primary"],
            "background": COLORS["accent_light"],
        },
        cursor="pointer",
        width="100%",
        transition="all 0.2s ease",
        on_drop=TaxAppState.handle_file_upload(
            rx.upload_files(upload_id="upload")
        ),
    )


# ============== API Key Modal Wrapper ==============
def api_modal() -> rx.Component:
    """API Key configuration modal."""
    return api_key_modal(
        is_open=TaxAppState.show_api_modal,
        on_close=TaxAppState.close_api_modal,
        api_key_value=TaxAppState.temp_api_key,
        on_api_key_change=TaxAppState.set_temp_api_key,
        on_save=TaxAppState.save_api_key_from_modal,
    )


# ============== Return Summary Modal ==============
def return_summary_modal() -> rx.Component:
    """Tax return summary modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("file-check", size=24, color=COLORS["success"]),
                    rx.text("Tax Return Summary", font_weight="600"),
                    spacing="2",
                ),
            ),
            rx.dialog.description(
                rx.vstack(
                    # Filing info
                    rx.hstack(
                        rx.text("Filing Status:", color=COLORS["text_muted"]),
                        rx.text(TaxAppState.filing_status.replace("_", " ").title(), font_weight="500"),
                        width="100%",
                        justify="between",
                    ),
                    rx.divider(),
                    
                    # Income summary
                    rx.text("Income", font_weight="600", color=COLORS["text_primary"]),
                    rx.hstack(
                        rx.text("Adjusted Gross Income:", color=COLORS["text_muted"]),
                        rx.text(f"${TaxAppState.adjusted_gross_income:,.2f}", font_weight="500"),
                        width="100%",
                        justify="between",
                    ),
                    rx.divider(),
                    
                    # Deductions
                    rx.text("Deductions", font_weight="600", color=COLORS["text_primary"]),
                    rx.hstack(
                        rx.text("Total Deductions:", color=COLORS["text_muted"]),
                        rx.text(f"${TaxAppState.total_deductions:,.2f}", font_weight="500"),
                        width="100%",
                        justify="between",
                    ),
                    rx.hstack(
                        rx.text("Taxable Income:", color=COLORS["text_muted"]),
                        rx.text(f"${TaxAppState.taxable_income:,.2f}", font_weight="500"),
                        width="100%",
                        justify="between",
                    ),
                    rx.divider(),
                    
                    # Tax calculation
                    rx.text("Tax Calculation", font_weight="600", color=COLORS["text_primary"]),
                    rx.hstack(
                        rx.text("Total Tax:", color=COLORS["text_muted"]),
                        rx.text(f"${TaxAppState.total_tax:,.2f}", font_weight="500", color=COLORS["danger"]),
                        width="100%",
                        justify="between",
                    ),
                    rx.hstack(
                        rx.text("Total Withholding:", color=COLORS["text_muted"]),
                        rx.text(f"${TaxAppState.total_withholding:,.2f}", font_weight="500", color=COLORS["success"]),
                        width="100%",
                        justify="between",
                    ),
                    rx.divider(),
                    
                    # Result
                    rx.hstack(
                        rx.cond(
                            TaxAppState.is_refund,
                            rx.hstack(
                                rx.icon("trending-up", color=COLORS["success"]),
                                rx.text("Estimated Refund:", font_weight="600"),
                                rx.text(f"+${TaxAppState.refund_or_owed:,.2f}", 
                                       font_size="24px", font_weight="700", color=COLORS["success"]),
                                spacing="2",
                            ),
                            rx.hstack(
                                rx.icon("trending-down", color=COLORS["danger"]),
                                rx.text("Amount Owed:", font_weight="600"),
                                rx.text(f"${abs(TaxAppState.refund_or_owed):,.2f}", 
                                       font_size="24px", font_weight="700", color=COLORS["danger"]),
                                spacing="2",
                            ),
                        ),
                        width="100%",
                        justify="center",
                        padding="16px",
                        background=COLORS["bg_subtle"],
                        border_radius="8px",
                    ),
                    
                    spacing="3",
                    width="100%",
                    padding="16px 0",
                ),
            ),
            rx.flex(
                rx.button(
                    rx.icon("download", size=16),
                    "Download Form 1040 PDF",
                    on_click=rx.download(
                        data=rx.Var.create(f"data:application/pdf;base64,") + TaxAppState.generated_pdf_base64,
                        filename="Form_1040_2024.pdf",
                    ),
                    color_scheme="indigo",
                ),
                rx.dialog.close(
                    rx.button("Close", variant="soft"),
                ),
                justify="end",
                spacing="3",
            ),
            style={"max_width": "500px"},
        ),
        open=TaxAppState.show_return_summary,
        on_open_change=lambda _: TaxAppState.close_return_summary(),
    )


# ============== Dashboard Page ==============
def dashboard_page() -> rx.Component:
    """Main dashboard page."""
    return page_container(
        api_modal(),
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text("Tax Dashboard", color=COLORS["text_primary"], 
                            font_size="32px", font_weight="700"),
                    rx.text(f"Tax Year {TaxAppState.tax_year}", color=COLORS["text_muted"]),
                    align_items="start",
                ),
                rx.spacer(),
                rx.link(
                    gradient_button("Upload Documents", icon="plus"),
                    href="/upload",
                ),
                width="100%",
                margin_bottom="32px",
            ),
            
            # Stats Row
            rx.hstack(
                stat_card(
                    "Total Income",
                    rx.cond(
                        TaxAppState.adjusted_gross_income > 0,
                        f"${TaxAppState.adjusted_gross_income:,.0f}",
                        "$0",
                    ),
                    "dollar-sign",
                    COLORS["success"],
                ),
                stat_card(
                    "Deductions",
                    rx.cond(
                        TaxAppState.total_deductions > 0,
                        f"${TaxAppState.total_deductions:,.0f}",
                        "$0",
                    ),
                    "circle-minus",
                    COLORS["warning"],
                ),
                stat_card(
                    "Estimated Tax",
                    rx.cond(
                        TaxAppState.total_tax > 0,
                        f"${TaxAppState.total_tax:,.0f}",
                        "$0",
                    ),
                    "calculator",
                    COLORS["error"],
                ),
                stat_card(
                    "Refund / Owed",
                    TaxAppState.formatted_refund,
                    "trending-up",
                    rx.cond(TaxAppState.is_refund, COLORS["success"], COLORS["error"]),
                ),
                spacing="4",
                flex_wrap="wrap",
                width="100%",
            ),
            
            # Content Grid
            rx.hstack(
                # Documents Section
                fintech_card(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Documents", color=COLORS["text_primary"], 
                                    font_size="18px", font_weight="600"),
                            rx.spacer(),
                            rx.text(f"{TaxAppState.parsed_documents.length()} files", 
                                    color=COLORS["text_muted"]),
                        ),
                        rx.cond(
                            TaxAppState.has_documents,
                            rx.vstack(
                                rx.foreach(TaxAppState.parsed_documents, document_card),
                                spacing="2",
                                width="100%",
                            ),
                            empty_state(
                                "folder-open",
                                "No documents yet",
                                "Upload your first document →",
                                "/upload"
                            ),
                        ),
                        width="100%",
                        spacing="4",
                    ),
                    flex="2",
                ),
                
                # Summary Section
                fintech_card(
                    rx.vstack(
                        rx.text("Tax Summary", color=COLORS["text_primary"], 
                                font_size="18px", font_weight="600"),
                        rx.divider(border_color=COLORS["border"]),
                        rx.vstack(
                            data_row("Filing Status", rx.text(
                                TaxAppState.filing_status.replace("_", " ").title(), 
                                color=COLORS["text_primary"], font_weight="500")),
                            data_row("Tax Year", rx.text(TaxAppState.tax_year, 
                                    color=COLORS["text_primary"], font_weight="500")),
                            data_row("W-2s", rx.text(f"{TaxAppState.w2_list.length()}", 
                                    color=COLORS["text_primary"], font_weight="500")),
                            data_row("1099s", rx.text(f"{TaxAppState.form_1099_list.length()}", 
                                    color=COLORS["text_primary"], font_weight="500")),
                            data_row(
                                "Status",
                                badge(
                                    TaxAppState.return_status.replace("_", " ").title(),
                                    rx.cond(
                                        TaxAppState.return_status == "complete",
                                        "green",
                                        "yellow"
                                    ),
                                ),
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        rx.spacer(),
                        rx.cond(
                            TaxAppState.can_generate_return,
                            rx.box(
                                gradient_button("Generate Tax Return", width="100%"),
                                width="100%",
                                on_click=TaxAppState.generate_return,
                            ),
                            rx.box(
                                rx.text("Generate Tax Return", text_align="center"),
                                width="100%",
                                background=COLORS["bg_hover"],
                                color=COLORS["text_muted"],
                                padding="12px",
                                border_radius="8px",
                                cursor="not-allowed",
                            ),
                        ),
                        width="100%",
                        height="100%",
                        spacing="4",
                    ),
                    flex="1",
                    min_width="300px",
                ),
                spacing="4",
                width="100%",
                margin_top="24px",
                align_items="stretch",
            ),
            
            # Error/Success Messages
            rx.cond(
                TaxAppState.error_message != "",
                rx.box(
                    rx.hstack(
                        rx.icon("circle-alert", size=16, color=COLORS["error"]),
                        rx.text(TaxAppState.error_message, color=COLORS["error"]),
                        spacing="2",
                    ),
                    background=COLORS["error_light"],
                    padding="12px 20px",
                    border_radius="8px",
                    width="100%",
                    margin_top="16px",
                ),
            ),
            rx.cond(
                TaxAppState.success_message != "",
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=16, color=COLORS["success"]),
                        rx.text(TaxAppState.success_message, color=COLORS["success"]),
                        spacing="2",
                    ),
                    background=COLORS["success_light"],
                    padding="12px 20px",
                    border_radius="8px",
                    width="100%",
                    margin_top="16px",
                ),
            ),
            
            width="100%",
            max_width="1200px",
            margin="0 auto",
            padding="100px 40px 40px 40px",
        ),
    )


# ============== Upload Page ==============
def upload_page() -> rx.Component:
    """Document upload page."""
    return page_container(
        api_modal(),
        rx.vstack(
            # Header row
            rx.hstack(
                rx.vstack(
                    rx.text("Upload Documents", color=COLORS["text_primary"], 
                            font_size="28px", font_weight="700"),
                    rx.text("Upload your W-2, 1099, and other tax documents",
                            color=COLORS["text_muted"], font_size="14px"),
                    align_items="start",
                    spacing="1",
                ),
                rx.spacer(),
                rx.link(gradient_button("Continue →"), href="/review"),
                width="100%",
            ),
            
            # API Key Notice (only shown if not configured)
            rx.cond(
                ~TaxAppState.has_api_key,
                rx.box(
                    rx.hstack(
                        rx.icon("circle-alert", size=16, color=COLORS["warning"]),
                        rx.text("API key required.", color="#b45309", font_size="14px"),
                        rx.text("Configure now →", color=COLORS["accent_primary"], 
                               cursor="pointer", font_weight="500",
                               on_click=TaxAppState.open_api_modal,
                               _hover={"text_decoration": "underline"}),
                        spacing="2",
                    ),
                    background=COLORS["warning_light"],
                    padding="12px 20px",
                    border_radius="8px",
                    width="100%",
                ),
            ),
            
            # Main content: Upload zone + Files list
            rx.cond(
                TaxAppState.has_api_key,
                # Has API key - show upload zone
                rx.vstack(
                    upload_zone_compact(),
                    
                    # Processing indicator with progress
                    rx.cond(
                        TaxAppState.processing,
                        rx.vstack(
                            rx.hstack(
                                rx.spinner(size="3", color=COLORS["accent_primary"]),
                                rx.text("Processing documents with AI...", color=COLORS["text_secondary"], font_size="14px"),
                                spacing="2",
                            ),
                            rx.text(
                                TaxAppState.processing_progress,
                                color=COLORS["text_muted"],
                                font_size="13px",
                            ),
                            # Progress bar
                            rx.progress(
                                value=TaxAppState.processing_file_index,
                                max=TaxAppState.processing_total_files,
                                width="100%",
                                color_scheme="indigo",
                            ),
                            spacing="2",
                            padding="12px 0",
                            width="100%",
                        ),
                    ),
                    
                    # Uploaded Files List
                    rx.cond(
                        TaxAppState.uploaded_files.length() > 0,
                        fintech_card(
                            rx.vstack(
                                rx.hstack(
                                    rx.text("Uploaded Files", color=COLORS["text_primary"], 
                                            font_size="15px", font_weight="600"),
                                    rx.spacer(),
                                    rx.text(f"{TaxAppState.uploaded_files.length()} files", 
                                            color=COLORS["text_muted"], font_size="13px"),
                                    width="100%",
                                ),
                                rx.foreach(
                                    TaxAppState.uploaded_files,
                                    lambda f: rx.hstack(
                                        rx.icon("file-text", size=16, color=COLORS["accent_primary"]),
                                        rx.text(f, color=COLORS["text_primary"], font_size="14px", flex="1"),
                                        rx.icon(
                                            "x",
                                            size=16,
                                            color=COLORS["text_muted"],
                                            cursor="pointer",
                                            _hover={"color": COLORS["error"]},
                                            on_click=lambda: TaxAppState.remove_file(f),
                                        ),
                                        spacing="3",
                                        width="100%",
                                        padding="10px 12px",
                                        background=COLORS["bg_hover"],
                                        border_radius="6px",
                                    ),
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            padding="16px",
                        ),
                        # No files yet - show hint
                        rx.box(
                            rx.hstack(
                                rx.icon("info", size=16, color=COLORS["text_muted"]),
                                rx.text("No files uploaded yet. Drop files above or click to browse.",
                                       color=COLORS["text_muted"], font_size="14px"),
                                spacing="2",
                            ),
                            padding="16px",
                            background=COLORS["bg_hover"],
                            border_radius="8px",
                            width="100%",
                        ),
                    ),
                    
                    spacing="3",
                    width="100%",
                ),
                # No API key - show setup prompt
                rx.box(
                    rx.hstack(
                        rx.icon("key", size=20, color=COLORS["text_muted"]),
                        rx.vstack(
                            rx.text("Configure API Key First", color=COLORS["text_primary"], 
                                    font_size="15px", font_weight="500"),
                            rx.text("You need a Gemini API key to parse documents", 
                                    color=COLORS["text_muted"], font_size="13px"),
                            align_items="start",
                            spacing="0",
                        ),
                        rx.spacer(),
                        rx.box(
                            rx.text("Set Up", font_size="14px"),
                            background=f"linear-gradient(135deg, {COLORS['accent_primary']} 0%, {COLORS['accent_purple']} 100%)",
                            color="white",
                            padding="8px 16px",
                            border_radius="6px",
                            font_weight="500",
                            cursor="pointer",
                            on_click=TaxAppState.open_api_modal,
                        ),
                        spacing="4",
                        padding="20px 24px",
                        width="100%",
                        align_items="center",
                    ),
                    border=f"2px dashed {COLORS['border']}",
                    border_radius="12px",
                    background="white",
                    width="100%",
                ),
            ),
            
            # Back link
            rx.link(
                rx.hstack(
                    rx.icon("arrow-left", size=14, color=COLORS["text_muted"]),
                    rx.text("Back to Dashboard", color=COLORS["text_muted"], font_size="14px"),
                    spacing="2",
                    _hover={"color": COLORS["text_primary"]},
                ),
                href="/",
                margin_top="16px",
            ),
            
            width="100%",
            max_width="600px",
            margin="0 auto",
            spacing="4",
            padding="100px 40px 40px 40px",
        ),
    )


# ============== Review Page ==============
# ============== Review Page Column Components ==============
def documents_column() -> rx.Component:
    """Left column: Documents & AI Processing."""
    return rx.box(
        rx.vstack(
            # File Selection Section
            rx.cond(
                TaxAppState.parsed_documents.length() > 0,
                fintech_card(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Documents", color=COLORS["text_primary"], 
                                    font_size="18px", font_weight="600"),
                            rx.spacer(),
                            rx.hstack(
                                rx.button(
                                    "Select All Pending",
                                    size="1",
                                    variant="outline",
                                    on_click=TaxAppState.select_all_pending,
                                ),
                                rx.button(
                                    "Clear",
                                    size="1",
                                    variant="ghost",
                                    on_click=TaxAppState.clear_selection,
                                ),
                                spacing="2",
                            ),
                        ),
                        rx.divider(border_color=COLORS["border"]),
                        
                        # File list with checkboxes
                        rx.foreach(
                            TaxAppState.parsed_documents,
                            lambda doc: rx.box(
                                rx.hstack(
                                    # Checkbox: for parsed docs = inclusion toggle, for pending = selection toggle
                                    rx.cond(
                                        doc["status"] == "parsed",
                                        # Parsed: checkbox toggles inclusion in calculation
                                        rx.box(
                                            rx.cond(
                                                doc["included"],
                                                rx.icon("square-check", size=20, color=COLORS["success"]),
                                                rx.icon("square", size=20, color=COLORS["text_muted"]),
                                            ),
                                            cursor="pointer",
                                            on_click=lambda: TaxAppState.toggle_document_inclusion(doc["name"]),
                                        ),
                                        # Pending: checkbox toggles selection for processing
                                        rx.box(
                                            rx.cond(
                                                TaxAppState.selected_files.contains(doc["name"]),
                                                rx.icon("square-check", size=20, color=COLORS["accent_primary"]),
                                                rx.icon("square", size=20, color=COLORS["text_muted"]),
                                            ),
                                        ),
                                    ),
                                    rx.vstack(
                                        rx.text(
                                            doc["name"], 
                                            color=rx.cond(
                                                doc["status"] == "parsed",
                                                rx.cond(doc["included"], COLORS["text_primary"], COLORS["text_muted"]),
                                                COLORS["text_primary"],
                                            ),
                                            font_size="14px",
                                            text_decoration=rx.cond(
                                                doc["status"] == "parsed",
                                                rx.cond(doc["included"], "none", "line-through"),
                                                "none",
                                            ),
                                        ),
                                        rx.text(
                                            rx.cond(
                                                doc["status"] == "parsed",
                                                rx.cond(
                                                    doc["included"],
                                                    f"✓ Included - {doc['type']}",
                                                    f"✗ Excluded - {doc['type']}",
                                                ),
                                                rx.cond(
                                                    doc["status"] == "error",
                                                    "⚠ Error - click to retry",
                                                    f"Pending - {doc['type']}",
                                                ),
                                            ),
                                            color=rx.cond(
                                                doc["status"] == "parsed",
                                                rx.cond(doc["included"], COLORS["success"], COLORS["text_muted"]),
                                                rx.cond(doc["status"] == "error", COLORS["warning"], COLORS["text_muted"]),
                                            ),
                                            font_size="12px",
                                        ),
                                        align_items="start",
                                        spacing="0",
                                        flex="1",
                                    ),
                                    rx.box(
                                        rx.icon("x", size=16, color=COLORS["text_muted"], _hover={"color": COLORS["error"]}),
                                        cursor="pointer",
                                        padding="4px",
                                        border_radius="4px",
                                        _hover={"background": COLORS["error_light"]},
                                        on_click=lambda: TaxAppState.remove_file(doc["name"]),
                                    ),
                                    width="100%",
                                    spacing="3",
                                ),
                                padding="12px 16px",
                                background=rx.cond(
                                    doc["status"] == "parsed",
                                    rx.cond(doc["included"], COLORS["success_light"], COLORS["bg_hover"]),
                                    rx.cond(TaxAppState.selected_files.contains(doc["name"]), "#EEF2FF", COLORS["bg_hover"]),
                                ),
                                border_radius="8px",
                                border=rx.cond(
                                    TaxAppState.selected_files.contains(doc["name"]),
                                    f"2px solid {COLORS['accent_primary']}",
                                    "2px solid transparent",
                                ),
                                cursor=rx.cond(doc["status"] == "parsed", "default", "pointer"),
                                on_click=lambda: TaxAppState.toggle_file_selection(doc["name"]),
                                transition="all 0.15s ease",
                            ),
                        ),
                        
                        # AI Process button
                        rx.cond(
                            ~TaxAppState.processing,
                            rx.button(
                                rx.icon("sparkles", size=16),
                                f"AI Process ({TaxAppState.selected_files.length()} selected)",
                                background=f"linear-gradient(135deg, {COLORS['accent_primary']} 0%, {COLORS['accent_purple']} 100%)",
                                color="white",
                                width="100%",
                                padding="12px 24px",
                                border_radius="8px",
                                cursor="pointer",
                                disabled=TaxAppState.selected_files.length() == 0,
                                on_click=TaxAppState.process_selected_files,
                            ),
                        ),
                        
                        spacing="3",
                        width="100%",
                    ),
                ),
                rx.box(
                    rx.hstack(
                        rx.icon("upload", size=20, color=COLORS["text_muted"]),
                        rx.text("No documents uploaded. Go to Upload page first.", color=COLORS["text_muted"]),
                        spacing="2",
                    ),
                    padding="24px",
                    background=COLORS["bg_hover"],
                    border_radius="12px",
                    text_align="center",
                ),
            ),
            
            # Success/Error messages
            rx.cond(
                TaxAppState.success_message != "",
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=16, color=COLORS["success"]),
                        rx.text(TaxAppState.success_message, color=COLORS["success"]),
                        spacing="2",
                    ),
                    padding="12px 16px",
                    background=COLORS["success_light"],
                    border_radius="8px",
                ),
            ),
            rx.cond(
                TaxAppState.error_message != "",
                rx.box(
                    rx.hstack(
                        rx.icon("circle-alert", size=16, color=COLORS["error"]),
                        rx.text(TaxAppState.error_message, color=COLORS["error"]),
                        spacing="2",
                    ),
                    padding="12px 16px",
                    background=COLORS["error_light"],
                    border_radius="8px",
                ),
            ),
            spacing="4",
            width="100%",
        ),
        flex="1",
        min_width="320px",
    )


def review_page() -> rx.Component:
    """Review and edit tax data page with responsive two-column layout."""
    return page_container(
        api_modal(),
        return_summary_modal(),
        # Processing overlay - shows full screen modal during AI processing
        processing_overlay(
            is_processing=TaxAppState.processing,
            current_file=TaxAppState.processing_current_file,
            file_index=TaxAppState.processing_file_index,
            total_files=TaxAppState.processing_total_files,
        ),
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text("Review Tax Data", color=COLORS["text_primary"], 
                            font_size="32px", font_weight="700"),
                    rx.text("Upload documents or add manual entries", color=COLORS["text_muted"]),
                    align_items="start",
                ),
                width="100%",
                margin_bottom="24px",
            ),
            
            # ===== TWO-COLUMN RESPONSIVE LAYOUT =====
            rx.hstack(
                # LEFT: Documents & AI Processing
                documents_column(),
                
                # RIGHT: Manual Entry
                rx.box(
                    fintech_card(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("pencil", size=20, color=COLORS["accent_primary"]),
                                rx.text("Manual Entry", color=COLORS["text_primary"], 
                                        font_size="18px", font_weight="600"),
                                rx.spacer(),
                                rx.text("Add income or deductions not from documents", 
                                        color=COLORS["text_muted"], font_size="13px"),
                            ),
                            rx.divider(border_color=COLORS["border"]),
                        
                        # Rental Property (Schedule E)
                        rx.vstack(
                        rx.hstack(
                            rx.text("🏠 Rental Properties (Schedule E)", 
                                    color=COLORS["text_primary"], font_weight="600"),
                            rx.spacer(),
                            rx.button("+ Add", size="1", on_click=TaxAppState.toggle_rental_form),
                        ),
                        rx.cond(
                            TaxAppState.rental_properties.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    TaxAppState.rental_properties,
                                    lambda p, idx: rx.box(
                                        rx.hstack(
                                            rx.vstack(
                                                rx.text(p["address"], color=COLORS["text_primary"], font_weight="600", font_size="15px"),
                                                rx.hstack(
                                                    rx.text(f"Rent: ${p['monthly_rent']:,.0f}/mo", color=COLORS["accent_primary"], font_size="13px"),
                                                    rx.text("→", color=COLORS["text_muted"], font_size="13px"),
                                                    rx.text(f"${p['rent_income']:,.0f}/yr", color=COLORS["success"], font_size="13px", font_weight="500"),
                                                    spacing="1",
                                                ),
                                                rx.text(f"Expenses: ${p['total_expenses']:,.0f}/yr", 
                                                        color=COLORS["text_muted"], font_size="12px"),
                                                align_items="start",
                                                spacing="1",
                                                flex="1",
                                            ),
                                            rx.vstack(
                                                rx.text("Net Income", color=COLORS["text_muted"], font_size="11px"),
                                                rx.text(f"${p['net_income']:,.0f}", 
                                                        color=rx.cond(p["net_income"].to(float) >= 0, COLORS["success"], COLORS["error"]),
                                                        font_weight="700",
                                                        font_size="18px"),
                                                rx.text("/year", color=COLORS["text_muted"], font_size="11px"),
                                                align_items="center",
                                                spacing="0",
                                            ),
                                            rx.box(
                                                rx.icon("x", size=16, color=COLORS["text_muted"]),
                                                cursor="pointer",
                                                padding="6px",
                                                border_radius="6px",
                                                _hover={"background": COLORS["error_light"], "color": COLORS["error"]},
                                                on_click=lambda: TaxAppState.remove_rental_property(idx),
                                            ),
                                            width="100%", spacing="4", align_items="center",
                                        ),
                                        padding="16px",
                                        background="white", 
                                        border_radius="10px", 
                                        border=f"1px solid {COLORS['border']}",
                                        box_shadow="0 1px 3px rgba(0,0,0,0.08)",
                                    ),
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            rx.text("No rental properties added", color=COLORS["text_muted"], font_style="italic"),
                        ),
                        # Rental Form
                        rx.cond(
                            TaxAppState.show_rental_form,
                            rx.vstack(
                                rx.input(
                                    placeholder="Address", 
                                    value=TaxAppState.rental_form_address, 
                                    on_change=TaxAppState.set_rental_address, 
                                    width="100%",
                                    background="white",
                                    border=f"1px solid {COLORS['border']}",
                                    color=COLORS["text_primary"],
                                    _placeholder={"color": COLORS["text_muted"]},
                                    padding="10px 12px",
                                    border_radius="8px",
                                    _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                ),
                                rx.hstack(
                                    rx.input(
                                        placeholder="Monthly Rent ($)", 
                                        value=TaxAppState.rental_form_income, 
                                        on_change=TaxAppState.set_rental_income, 
                                        type="number",
                                        background="white",
                                        border=f"1px solid {COLORS['border']}",
                                        color=COLORS["text_primary"],
                                        _placeholder={"color": COLORS["text_muted"]},
                                        padding="10px 12px",
                                        border_radius="8px",
                                        _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                    ),
                                    rx.input(
                                        placeholder="Mortgage Interest ($)", 
                                        value=TaxAppState.rental_form_mortgage, 
                                        on_change=TaxAppState.set_rental_mortgage, 
                                        type="number",
                                        background="white",
                                        border=f"1px solid {COLORS['border']}",
                                        color=COLORS["text_primary"],
                                        _placeholder={"color": COLORS["text_muted"]},
                                        padding="10px 12px",
                                        border_radius="8px",
                                        _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                    ),
                                    width="100%",
                                    spacing="3",
                                ),
                                rx.hstack(
                                    rx.input(
                                        placeholder="Property Tax (Quarterly $)", 
                                        value=TaxAppState.rental_form_tax, 
                                        on_change=TaxAppState.set_rental_tax, 
                                        type="number",
                                        background="white",
                                        border=f"1px solid {COLORS['border']}",
                                        color=COLORS["text_primary"],
                                        _placeholder={"color": COLORS["text_muted"]},
                                        padding="10px 12px",
                                        border_radius="8px",
                                        _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                    ),
                                    rx.input(
                                        placeholder="Insurance ($)", 
                                        value=TaxAppState.rental_form_insurance, 
                                        on_change=TaxAppState.set_rental_insurance, 
                                        type="number",
                                        background="white",
                                        border=f"1px solid {COLORS['border']}",
                                        color=COLORS["text_primary"],
                                        _placeholder={"color": COLORS["text_muted"]},
                                        padding="10px 12px",
                                        border_radius="8px",
                                        _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                    ),
                                    width="100%",
                                    spacing="3",
                                ),
                                rx.hstack(
                                    rx.input(
                                        placeholder="Repairs ($)", 
                                        value=TaxAppState.rental_form_repairs, 
                                        on_change=TaxAppState.set_rental_repairs, 
                                        type="number",
                                        background="white",
                                        border=f"1px solid {COLORS['border']}",
                                        color=COLORS["text_primary"],
                                        _placeholder={"color": COLORS["text_muted"]},
                                        padding="10px 12px",
                                        border_radius="8px",
                                        _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                    ),
                                    rx.input(
                                        placeholder="Depreciation ($)", 
                                        value=TaxAppState.rental_form_depreciation, 
                                        on_change=TaxAppState.set_rental_depreciation, 
                                        type="number",
                                        background="white",
                                        border=f"1px solid {COLORS['border']}",
                                        color=COLORS["text_primary"],
                                        _placeholder={"color": COLORS["text_muted"]},
                                        padding="10px 12px",
                                        border_radius="8px",
                                        _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                    ),
                                    width="100%",
                                    spacing="3",
                                ),
                                rx.input(
                                    placeholder="Other Expenses ($)", 
                                    value=TaxAppState.rental_form_other, 
                                    on_change=TaxAppState.set_rental_other, 
                                    type="number", 
                                    width="100%",
                                    background="white",
                                    border=f"1px solid {COLORS['border']}",
                                    color=COLORS["text_primary"],
                                    _placeholder={"color": COLORS["text_muted"]},
                                    padding="10px 12px",
                                    border_radius="8px",
                                    _focus={"border_color": COLORS["accent_primary"], "box_shadow": f"0 0 0 3px {COLORS['accent_light']}"},
                                ),
                                rx.hstack(
                                    rx.button("Cancel", variant="outline", on_click=TaxAppState.toggle_rental_form),
                                    rx.button("Add Property", on_click=TaxAppState.submit_rental_form),
                                    width="100%", justify="end", spacing="3",
                                ),
                                width="100%", spacing="3", padding="16px", 
                                background=COLORS["bg_page"], border_radius="8px", border=f"1px solid {COLORS['border']}",
                            ),
                        ),
                        rx.text(f"Total Rental Income: ${TaxAppState.total_rental_income:,.2f}", 
                                color=COLORS["success"], font_size="13px"),
                        width="100%", spacing="2", padding="12px", 
                        background=COLORS["bg_hover"], border_radius="8px",
                        ),
                        
                        # Business Income (Schedule C)
                        rx.vstack(
                        rx.hstack(
                            rx.text("💼 Business Income (Schedule C)", 
                                    color=COLORS["text_primary"], font_weight="600"),
                            rx.spacer(),
                            rx.button("+ Add", size="1", on_click=TaxAppState.toggle_business_form),
                        ),
                        rx.cond(
                            TaxAppState.business_income.length() > 0,
                            rx.foreach(
                                TaxAppState.business_income,
                                lambda b, idx: rx.hstack(
                                    rx.text(b["name"], flex="1"),
                                    rx.text(f"Net: ${b['net_profit']:,.2f}",
                                            color=rx.cond(b["net_profit"].to(float) >= 0, COLORS["success"], COLORS["error"])),
                                    rx.icon("x", size=14, cursor="pointer",
                                            on_click=lambda: TaxAppState.remove_business(idx)),
                                    width="100%", padding="8px",
                                ),
                            ),
                            rx.text("No businesses added", color=COLORS["text_muted"], font_style="italic"),
                        ),
                        # Business Form
                        rx.cond(
                            TaxAppState.show_business_form,
                            rx.vstack(
                                styled_input("Business Name", TaxAppState.business_form_name, TaxAppState.set_business_name),
                                rx.hstack(
                                    styled_input("Gross Income ($)", TaxAppState.business_form_income, TaxAppState.set_business_income, "number"),
                                    styled_input("Total Expenses ($)", TaxAppState.business_form_expenses, TaxAppState.set_business_expenses, "number"),
                                    width="100%",
                                    spacing="3",
                                ),
                                rx.hstack(
                                    rx.button("Cancel", variant="outline", on_click=TaxAppState.toggle_business_form),
                                    rx.button("Add Business", on_click=TaxAppState.submit_business_form),
                                    width="100%", justify="end", spacing="3",
                                ),
                                width="100%", spacing="3", padding="16px", 
                                background=COLORS["bg_page"], border_radius="8px", border=f"1px solid {COLORS['border']}",
                            ),
                        ),
                        rx.text(f"Total Business Income: ${TaxAppState.total_business_income:,.2f}", 
                                color=COLORS["success"], font_size="13px"),
                        rx.cond(
                            TaxAppState.self_employment_tax > 0,
                            rx.text(f"Self-Employment Tax: ${TaxAppState.self_employment_tax:,.2f}", 
                                    color=COLORS["warning"], font_size="13px"),
                        ),
                        width="100%", spacing="2", padding="12px", 
                        background=COLORS["bg_hover"], border_radius="8px",
                        ),
                        
                        # Other Income
                        rx.vstack(
                        rx.hstack(
                            rx.text("📋 Other Income", color=COLORS["text_primary"], font_weight="600"),
                            rx.spacer(),
                            rx.button("+ Add", size="1", on_click=TaxAppState.toggle_other_income_form),
                        ),
                        rx.cond(
                            TaxAppState.other_income.length() > 0,
                            rx.foreach(
                                TaxAppState.other_income,
                                lambda i, idx: rx.hstack(
                                    rx.text(i["description"], flex="1"),
                                    rx.text(f"${i['amount']:,.2f}", color=COLORS["success"]),
                                    rx.icon("x", size=14, cursor="pointer",
                                            on_click=lambda: TaxAppState.remove_other_income(idx)),
                                    width="100%", padding="8px",
                                ),
                            ),
                            rx.text("No other income added", color=COLORS["text_muted"], font_style="italic"),
                        ),
                        rx.cond(
                            TaxAppState.show_other_income_form,
                            rx.hstack(
                                styled_input("Description", TaxAppState.other_income_form_desc, TaxAppState.set_other_income_desc),
                                styled_input("Amount ($)", TaxAppState.other_income_form_amount, TaxAppState.set_other_income_amount, "number", "140px"),
                                rx.button("Add", on_click=TaxAppState.submit_other_income_form),
                                width="100%",
                                spacing="3",
                                padding="8px 0",
                            ),
                        ),
                        width="100%", spacing="2", padding="12px", 
                        background=COLORS["bg_hover"], border_radius="8px",
                        ),
                        
                        # Other Deductions
                        rx.vstack(
                        rx.hstack(
                            rx.text("📉 Other Deductions", color=COLORS["text_primary"], font_weight="600"),
                            rx.spacer(),
                            rx.button("+ Add", size="1", on_click=TaxAppState.toggle_other_deduction_form),
                        ),
                        rx.cond(
                            TaxAppState.other_deductions.length() > 0,
                            rx.foreach(
                                TaxAppState.other_deductions,
                                lambda d, idx: rx.hstack(
                                    rx.text(d["description"], flex="1"),
                                    rx.text(f"-${d['amount']:,.2f}", color=COLORS["success"]),
                                    rx.icon("x", size=14, cursor="pointer",
                                            on_click=lambda: TaxAppState.remove_other_deduction(idx)),
                                    width="100%", padding="8px",
                                ),
                            ),
                            rx.text("No deductions added", color=COLORS["text_muted"], font_style="italic"),
                        ),
                        rx.cond(
                            TaxAppState.show_other_deduction_form,
                            rx.hstack(
                                styled_input("Description", TaxAppState.other_deduction_form_desc, TaxAppState.set_other_deduction_desc),
                                styled_input("Amount ($)", TaxAppState.other_deduction_form_amount, TaxAppState.set_other_deduction_amount, "number", "140px"),
                                rx.button("Add", on_click=TaxAppState.submit_other_deduction_form),
                                width="100%",
                                spacing="3",
                                padding="8px 0",
                            ),
                        ),
                        width="100%", spacing="2", padding="12px", 
                        background=COLORS["bg_hover"], border_radius="8px",
                        ),
                        
                        # Dependents & Child Tax Credit
                        rx.vstack(
                        rx.hstack(
                            rx.text("👨‍👩‍👧‍👦 Dependents", color=COLORS["text_primary"], font_weight="600"),
                            rx.spacer(),
                            rx.button("+ Add", size="1", on_click=TaxAppState.toggle_dependent_form),
                        ),
                        rx.cond(
                            TaxAppState.dependents.length() > 0,
                            rx.foreach(
                                TaxAppState.dependents,
                                lambda d, idx: rx.hstack(
                                    rx.text(d["name"], flex="1"),
                                    rx.text(f"{d['relationship']}, Age {d['age']}"),
                                    rx.badge(
                                        rx.cond(d["is_child"], "CTC $2,000", "Credit $500"),
                                        color_scheme=rx.cond(d["is_child"], "green", "blue"),
                                    ),
                                    rx.icon("x", size=14, cursor="pointer",
                                            on_click=lambda: TaxAppState.remove_dependent(idx)),
                                    width="100%", padding="8px",
                                ),
                            ),
                            rx.text("No dependents added", color=COLORS["text_muted"], font_style="italic"),
                        ),
                        # Dependent Form
                        rx.cond(
                            TaxAppState.show_dependent_form,
                            rx.vstack(
                                rx.hstack(
                                    styled_input("Name", TaxAppState.dependent_form_name, TaxAppState.set_dependent_name),
                                    styled_input("Relationship", TaxAppState.dependent_form_relationship, TaxAppState.set_dependent_relationship, "text", "140px"),
                                    styled_input("Age", TaxAppState.dependent_form_age, TaxAppState.set_dependent_age, "number", "80px"),
                                    width="100%",
                                    spacing="3",
                                ),
                                rx.text("Under 17 = $2,000 Child Tax Credit | 17+ = $500 Other Dependent Credit", 
                                        color=COLORS["text_muted"], font_size="12px"),
                                rx.hstack(
                                    rx.button("Cancel", variant="outline", on_click=TaxAppState.toggle_dependent_form),
                                    rx.button("Add Dependent", on_click=TaxAppState.submit_dependent_form),
                                    width="100%", justify="end", spacing="3",
                                ),
                                width="100%", spacing="3", padding="16px", 
                                background=COLORS["bg_page"], border_radius="8px", border=f"1px solid {COLORS['border']}",
                            ),
                        ),
                        # Credits Summary
                        rx.cond(
                            TaxAppState.child_tax_credit > 0,
                            rx.text(f"Child Tax Credit: ${TaxAppState.child_tax_credit:,.2f}", 
                                    color=COLORS["success"], font_size="13px"),
                        ),
                        rx.cond(
                            TaxAppState.other_dependent_credit > 0,
                            rx.text(f"Other Dependent Credit: ${TaxAppState.other_dependent_credit:,.2f}", 
                                    color=COLORS["success"], font_size="13px"),
                        ),
                        rx.text(f"Total Tax Credits: ${TaxAppState.total_credits:,.2f}", 
                                color=COLORS["success"], font_size="13px", font_weight="600"),
                        width="100%", spacing="2", padding="12px", 
                        background=COLORS["bg_hover"], border_radius="8px",
                        ),
                        
                        spacing="4",
                        width="100%",
                        ),
                ),
                flex="1",
                min_width="320px",
            ),
            # END TWO-COLUMN LAYOUT
            flex_wrap="wrap",
            spacing="6",
            width="100%",
            align_items="stretch",
        ),
        
        # Income Section
        fintech_card(
                rx.vstack(
                    rx.hstack(
                        rx.text("Income", color=COLORS["text_primary"], 
                                font_size="18px", font_weight="600"),
                        rx.spacer(),
                        rx.text(f"Total: ${TaxAppState.adjusted_gross_income:,.2f}", 
                                color=COLORS["success"], font_weight="600"),
                    ),
                    rx.divider(border_color=COLORS["border"]),
                    
                    # W-2 Section
                    rx.vstack(
                        rx.hstack(
                            rx.text("W-2 Wages", color=COLORS["text_primary"], font_weight="600"),
                            rx.spacer(),
                            rx.text(f"${TaxAppState.total_wages:,.2f}", 
                                    color=COLORS["success"], font_weight="500"),
                        ),
                        rx.cond(
                            TaxAppState.w2_list.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    TaxAppState.w2_list,
                                    lambda w2: rx.hstack(
                                        rx.text(w2["employer_name"], color=COLORS["text_secondary"]),
                                        rx.spacer(),
                                        rx.text(f"${w2['wages']:,.2f}", 
                                                color=COLORS["text_primary"], font_weight="500"),
                                        width="100%",
                                        padding="8px 0",
                                    ),
                                ),
                                width="100%",
                            ),
                            rx.text("No W-2s added", color=COLORS["text_muted"], font_style="italic"),
                        ),
                        width="100%",
                        spacing="2",
                        padding="16px",
                        background=COLORS["bg_hover"],
                        border_radius="12px",
                    ),
                    
                    # 1099 Section
                    rx.vstack(
                        rx.hstack(
                            rx.text("1099 Income", color=COLORS["text_primary"], font_weight="600"),
                            rx.spacer(),
                            rx.text(f"${TaxAppState.total_interest + TaxAppState.total_dividends + TaxAppState.total_other_income:,.2f}", 
                                    color=COLORS["success"], font_weight="500"),
                        ),
                        rx.cond(
                            TaxAppState.form_1099_list.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    TaxAppState.form_1099_list,
                                    lambda f: rx.hstack(
                                        badge(f["form_type"], "blue"),
                                        rx.text(f["payer_name"], color=COLORS["text_secondary"]),
                                        rx.spacer(),
                                        rx.text(f"${f['amount']:,.2f}", 
                                                color=COLORS["text_primary"], font_weight="500"),
                                        width="100%",
                                        padding="8px 0",
                                    ),
                                ),
                                width="100%",
                            ),
                            rx.text("No 1099s added", color=COLORS["text_muted"], font_style="italic"),
                        ),
                        width="100%",
                        spacing="2",
                        padding="16px",
                        background=COLORS["bg_hover"],
                        border_radius="12px",
                        margin_top="12px",
                    ),
                    
                    width="100%",
                    spacing="3",
                ),
                width="100%",
            ),
            
            # Tax Calculation Summary
            fintech_card(
                rx.vstack(
                    rx.text("Tax Calculation", color=COLORS["text_primary"], 
                            font_size="18px", font_weight="600"),
                    rx.divider(border_color=COLORS["border"]),
                    rx.vstack(
                        data_row("Adjusted Gross Income", 
                                rx.text(f"${TaxAppState.adjusted_gross_income:,.2f}", 
                                        color=COLORS["text_primary"], font_weight="500")),
                        data_row("Standard Deduction", 
                                rx.text(f"-${TaxAppState.total_deductions:,.2f}", 
                                        color=COLORS["warning"], font_weight="500")),
                        data_row("Taxable Income", 
                                rx.text(f"${TaxAppState.taxable_income:,.2f}", 
                                        color=COLORS["text_primary"], font_weight="600")),
                        rx.divider(border_color=COLORS["border"]),
                        data_row("Total Tax", 
                                rx.text(f"${TaxAppState.total_tax:,.2f}", 
                                        color=COLORS["error"], font_weight="500")),
                        data_row("Total Withholding", 
                                rx.text(f"${TaxAppState.total_withholding:,.2f}", 
                                        color=COLORS["accent_primary"], font_weight="500")),
                        rx.divider(border_color=COLORS["border"]),
                        data_row(
                            rx.cond(TaxAppState.is_refund, "Estimated Refund", "Amount Owed"),
                            rx.text(
                                TaxAppState.formatted_refund,
                                color=rx.cond(TaxAppState.is_refund, COLORS["success"], COLORS["error"]),
                                font_size="24px",
                                font_weight="700",
                            ),
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    spacing="3",
                ),
                width="100%",
                margin_top="24px",
            ),
            
            # Action Buttons
            rx.hstack(
                rx.link(outline_button("← Back"), href="/"),
                rx.cond(
                    TaxAppState.can_generate_return,
                    rx.box(
                        gradient_button("Generate Tax Return"),
                        on_click=TaxAppState.generate_return,
                    ),
                    rx.box(
                        gradient_button("Generate Tax Return"),
                        opacity="0.5",
                        cursor="not-allowed",
                    ),
                ),
                spacing="4",
                margin_top="32px",
            ),
            
            width="100%",
            max_width="1400px",
            margin="0 auto",
            padding="100px 40px 40px 40px",
        ),
    )


# ============== Settings Page ==============
def settings_page() -> rx.Component:
    """Settings page."""
    return page_container(
        api_modal(),
        rx.vstack(
            rx.hstack(
                rx.text("Settings", color=COLORS["text_primary"], 
                        font_size="32px", font_weight="700"),
                rx.spacer(),
                # Save button
                rx.button(
                    rx.icon("check", size=16),
                    "Save Settings",
                    background=f"linear-gradient(135deg, {COLORS['accent_primary']} 0%, {COLORS['accent_purple']} 100%)",
                    color="white",
                    padding="12px 24px",
                    border_radius="8px",
                    on_click=TaxAppState.save_settings,
                ),
                width="100%",
            ),
            
            # Success message
            rx.cond(
                TaxAppState.success_message != "",
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=16, color=COLORS["success"]),
                        rx.text(TaxAppState.success_message, color=COLORS["success"]),
                        spacing="2",
                    ),
                    background=COLORS["success_light"],
                    padding="12px 20px",
                    border_radius="8px",
                    width="100%",
                    margin_top="8px",
                ),
            ),
            
            # API Keys Section
            fintech_card(
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("key", size=20, color=COLORS["accent_primary"]),
                            background=COLORS["accent_light"],
                            padding="10px",
                            border_radius="8px",
                        ),
                        rx.text("API Configuration", color=COLORS["text_primary"], 
                                font_size="18px", font_weight="600"),
                        spacing="3",
                    ),
                    rx.divider(border_color=COLORS["border"]),
                    rx.text(
                        "Enter your Google Gemini API key for document parsing. FREE - 1500 requests/day!",
                        color=COLORS["text_muted"],
                        font_size="14px",
                    ),
                    rx.vstack(
                        rx.text("Gemini API Key", color=COLORS["text_secondary"], 
                               font_size="14px", font_weight="500"),
                        rx.input(
                            placeholder="AIza...",
                            type="password",
                            value=TaxAppState.settings_api_key_input,
                            on_change=TaxAppState.set_settings_api_key,
                            background=COLORS["bg_input"],
                            border=f"1px solid {COLORS['border']}",
                            color=COLORS["text_primary"],
                            padding="12px 16px",
                            border_radius="8px",
                            width="100%",
                            _focus={
                                "border_color": COLORS["accent_primary"],
                                "box_shadow": f"0 0 0 3px {COLORS['accent_light']}",
                            },
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.link(
                        rx.hstack(
                            rx.text("Get FREE API key from aistudio.google.com"),
                            rx.icon("external-link", size=14),
                            spacing="2",
                            color=COLORS["accent_primary"],
                            font_size="13px",
                            font_weight="500",
                        ),
                        href="https://aistudio.google.com/apikey",
                        is_external=True,
                    ),
                    # Status indicator (shows saved state, not input)
                    rx.cond(
                        TaxAppState.has_api_key,
                        rx.hstack(
                            rx.icon("circle-check", size=14, color=COLORS["success"]),
                            rx.text("API key configured", color=COLORS["success"], 
                                   font_size="13px", font_weight="500"),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.icon("circle-alert", size=14, color=COLORS["warning"]),
                            rx.text("API key not configured", color="#b45309", 
                                   font_size="13px", font_weight="500"),
                            spacing="2",
                        ),
                    ),
                    width="100%",
                    spacing="4",
                ),
                width="100%",
                margin_top="16px",
            ),
            
            # Filing Options
            fintech_card(
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("file-text", size=20, color=COLORS["accent_primary"]),
                            background=COLORS["accent_light"],
                            padding="10px",
                            border_radius="8px",
                        ),
                        rx.text("Filing Options", color=COLORS["text_primary"], 
                                font_size="18px", font_weight="600"),
                        spacing="3",
                    ),
                    rx.divider(border_color=COLORS["border"]),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Filing Status", color=COLORS["text_secondary"], 
                                   font_size="14px", font_weight="500"),
                            rx.select(
                                ["single", "married_filing_jointly", "married_filing_separately", 
                                 "head_of_household", "qualifying_widow"],
                                value=TaxAppState.filing_status,
                                on_change=TaxAppState.set_filing_status,
                                width="240px",
                            ),
                            align_items="start",
                        ),
                        rx.vstack(
                            rx.text("Tax Year", color=COLORS["text_secondary"], 
                                   font_size="14px", font_weight="500"),
                            rx.select(
                                ["2024", "2025"],
                                value=str(TaxAppState.tax_year),
                                width="120px",
                            ),
                            align_items="start",
                        ),
                        spacing="6",
                        flex_wrap="wrap",
                    ),
                    width="100%",
                    spacing="4",
                ),
                width="100%",
                margin_top="24px",
            ),
            
            # Danger Zone
            fintech_card(
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            rx.icon("trash-2", size=20, color=COLORS["error"]),
                            background=COLORS["error_light"],
                            padding="10px",
                            border_radius="8px",
                        ),
                        rx.text("Danger Zone", color=COLORS["error"], 
                                font_size="18px", font_weight="600"),
                        spacing="3",
                    ),
                    rx.divider(border_color=COLORS["border"]),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Clear All Data", color=COLORS["text_primary"], font_weight="500"),
                            rx.text("Delete all uploaded documents and tax data", 
                                    color=COLORS["text_muted"], font_size="13px"),
                            align_items="start",
                        ),
                        rx.spacer(),
                        rx.box(
                            rx.text("Clear All"),
                            background=COLORS["error_light"],
                            color=COLORS["error"],
                            padding="8px 16px",
                            border_radius="8px",
                            cursor="pointer",
                            font_weight="500",
                            on_click=TaxAppState.clear_all,
                            _hover={"opacity": "0.8"},
                        ),
                        width="100%",
                        align_items="center",
                    ),
                    width="100%",
                    spacing="4",
                ),
                width="100%",
                margin_top="24px",
                border=f"1px solid {COLORS['error_light']}",
            ),
            
            rx.link(outline_button("← Back to Dashboard"), href="/", margin_top="24px"),
            
            width="100%",
            max_width="600px",
            margin="0 auto",
            padding="100px 40px 40px 40px",
            on_mount=TaxAppState.load_settings,
        ),
    )


# ============== App Configuration ==============
app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="indigo",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    style={
        "font_family": "Inter, sans-serif",
        "background": COLORS["bg_page"],
    },
)

# Register pages
app.add_page(dashboard_page, route="/", title="TaxSnapPro - Dashboard", on_load=TaxAppState.load_saved_data)
app.add_page(upload_page, route="/upload", title="TaxSnapPro - Upload")
app.add_page(review_page, route="/review", title="TaxSnapPro - Review")
app.add_page(settings_page, route="/settings", title="TaxSnapPro - Settings")
