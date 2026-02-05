"""
AI Tax - Main Application (Mercury Style UI)
"""
import reflex as rx
from .state import TaxAppState
from .components import (
    COLORS, mercury_card, gradient_button, outline_button, stat_card,
    section_header, empty_state, badge, data_row, document_card,
    nav_bar, page_container,
)


# ============== Upload Zone ==============
def upload_zone() -> rx.Component:
    """File upload dropzone."""
    return rx.upload(
        rx.vstack(
            rx.icon("upload", size=48, color="rgba(59, 130, 246, 0.8)"),
            rx.text("Drop your tax documents here", color="white", 
                    font_size="18px", font_weight="500"),
            rx.text("W-2, 1099, 1098, or any tax forms", 
                    color=COLORS["text_muted"], font_size="14px"),
            gradient_button("Browse Files", margin_top="16px"),
            align_items="center",
            spacing="3",
            padding="60px",
        ),
        id="upload",
        border="2px dashed rgba(59, 130, 246, 0.3)",
        border_radius="16px",
        background="rgba(30, 41, 59, 0.3)",
        _hover={
            "border_color": "rgba(59, 130, 246, 0.6)",
            "background": "rgba(30, 41, 59, 0.5)"
        },
        cursor="pointer",
        width="100%",
        max_width="600px",
        on_drop=TaxAppState.handle_file_upload(
            rx.upload_files(upload_id="upload")
        ),
    )


# ============== Dashboard Page ==============
def dashboard_page() -> rx.Component:
    """Main dashboard page."""
    return page_container(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text("Tax Dashboard", color="white", font_size="32px", font_weight="600"),
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
                mercury_card(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Documents", color="white", font_size="18px", font_weight="500"),
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
                mercury_card(
                    rx.vstack(
                        rx.text("Tax Summary", color="white", font_size="18px", font_weight="500"),
                        rx.divider(border_color=COLORS["border"]),
                        rx.vstack(
                            data_row("Filing Status", rx.text(TaxAppState.filing_status.capitalize(), color="white")),
                            data_row("Tax Year", rx.text(TaxAppState.tax_year, color="white")),
                            data_row("W-2s", rx.text(f"{TaxAppState.w2_list.length()}", color="white")),
                            data_row("1099s", rx.text(f"{TaxAppState.form_1099_list.length()}", color="white")),
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
                                background=f"linear-gradient(135deg, {COLORS['accent_blue']} 0%, {COLORS['accent_purple']} 100%)",
                                color="white",
                                padding="12px",
                                border_radius="8px",
                                opacity="0.5",
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
                    rx.text(TaxAppState.error_message),
                    background="rgba(239, 68, 68, 0.2)",
                    color=COLORS["error"],
                    padding="12px 20px",
                    border_radius="8px",
                    width="100%",
                    margin_top="16px",
                ),
            ),
            rx.cond(
                TaxAppState.success_message != "",
                rx.box(
                    rx.text(TaxAppState.success_message),
                    background="rgba(16, 185, 129, 0.2)",
                    color=COLORS["success"],
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
        rx.vstack(
            rx.text("Upload Documents", color="white", font_size="32px", font_weight="600"),
            rx.text(
                "Upload your W-2, 1099, and other tax documents. We'll extract the data automatically.",
                color=COLORS["text_muted"],
                font_size="16px",
                text_align="center",
                max_width="500px",
            ),
            
            upload_zone(),
            
            # Uploaded Files List
            rx.cond(
                TaxAppState.uploaded_files.length() > 0,
                mercury_card(
                    rx.vstack(
                        rx.text("Uploaded Files", color="white", font_size="16px", font_weight="500"),
                        rx.foreach(
                            TaxAppState.uploaded_files,
                            lambda f: rx.hstack(
                                rx.icon("file", size=16, color=COLORS["accent_blue"]),
                                rx.text(f, color="white"),
                                spacing="2",
                            ),
                        ),
                        spacing="2",
                    ),
                    margin_top="24px",
                    width="100%",
                    max_width="600px",
                ),
            ),
            
            # Navigation Buttons
            rx.hstack(
                rx.link(outline_button("← Back to Dashboard"), href="/"),
                rx.link(gradient_button("Continue to Review →"), href="/review"),
                spacing="4",
                margin_top="32px",
            ),
            
            align_items="center",
            spacing="4",
            padding="120px 40px 40px 40px",
        ),
    )


# ============== Review Page ==============
def review_page() -> rx.Component:
    """Review and edit tax data page."""
    return page_container(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text("Review Tax Data", color="white", font_size="32px", font_weight="600"),
                    rx.text("Verify and edit your tax information", color=COLORS["text_muted"]),
                    align_items="start",
                ),
                rx.spacer(),
                gradient_button("Save Changes"),
                width="100%",
                margin_bottom="32px",
            ),
            
            # Income Section
            mercury_card(
                rx.vstack(
                    rx.hstack(
                        rx.text("Income", color="white", font_size="18px", font_weight="500"),
                        rx.spacer(),
                        rx.text(f"Total: ${TaxAppState.adjusted_gross_income:,.2f}", 
                                color=COLORS["success"], font_weight="500"),
                    ),
                    rx.divider(border_color=COLORS["border"]),
                    
                    # W-2 Section
                    rx.vstack(
                        rx.hstack(
                            rx.text("W-2 Wages", color="white", font_weight="500"),
                            rx.spacer(),
                            rx.text(f"${TaxAppState.total_wages:,.2f}", color=COLORS["success"]),
                        ),
                        rx.cond(
                            TaxAppState.w2_list.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    TaxAppState.w2_list,
                                    lambda w2: rx.hstack(
                                        rx.text(w2["employer_name"], color=COLORS["text_secondary"]),
                                        rx.spacer(),
                                        rx.text(f"${w2['wages']:,.2f}", color="white"),
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
                        background="rgba(30, 41, 59, 0.3)",
                        border_radius="8px",
                    ),
                    
                    # 1099 Section
                    rx.vstack(
                        rx.hstack(
                            rx.text("1099 Income", color="white", font_weight="500"),
                            rx.spacer(),
                            rx.text(f"${TaxAppState.total_interest + TaxAppState.total_dividends + TaxAppState.total_other_income:,.2f}", 
                                    color=COLORS["success"]),
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
                                        rx.text(f"${f['amount']:,.2f}", color="white"),
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
                        background="rgba(30, 41, 59, 0.3)",
                        border_radius="8px",
                        margin_top="12px",
                    ),
                    
                    width="100%",
                    spacing="3",
                ),
                width="100%",
            ),
            
            # Tax Calculation Summary
            mercury_card(
                rx.vstack(
                    rx.text("Tax Calculation", color="white", font_size="18px", font_weight="500"),
                    rx.divider(border_color=COLORS["border"]),
                    rx.vstack(
                        data_row("Adjusted Gross Income", 
                                rx.text(f"${TaxAppState.adjusted_gross_income:,.2f}", color="white")),
                        data_row("Standard Deduction", 
                                rx.text(f"-${TaxAppState.total_deductions:,.2f}", color=COLORS["warning"])),
                        data_row("Taxable Income", 
                                rx.text(f"${TaxAppState.taxable_income:,.2f}", color="white", font_weight="500")),
                        rx.divider(border_color=COLORS["border"]),
                        data_row("Total Tax", 
                                rx.text(f"${TaxAppState.total_tax:,.2f}", color=COLORS["error"])),
                        data_row("Total Withholding", 
                                rx.text(f"${TaxAppState.total_withholding:,.2f}", color=COLORS["accent_blue"])),
                        rx.divider(border_color=COLORS["border"]),
                        data_row(
                            rx.cond(TaxAppState.is_refund, "Estimated Refund", "Amount Owed"),
                            rx.text(
                                TaxAppState.formatted_refund,
                                color=rx.cond(TaxAppState.is_refund, COLORS["success"], COLORS["error"]),
                                font_size="20px",
                                font_weight="600",
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
            max_width="800px",
            margin="0 auto",
            padding="100px 40px 40px 40px",
        ),
    )


# ============== Settings Page ==============
def settings_page() -> rx.Component:
    """Settings page."""
    return page_container(
        rx.vstack(
            rx.text("Settings", color="white", font_size="32px", font_weight="600"),
            
            # API Keys Section
            mercury_card(
                rx.vstack(
                    rx.text("API Configuration", color="white", font_size="18px", font_weight="500"),
                    rx.divider(border_color=COLORS["border"]),
                    rx.text(
                        "Enter your OpenAI API key for document parsing. Your key is stored locally and never sent to our servers.",
                        color=COLORS["text_muted"],
                        font_size="14px",
                    ),
                    rx.input(
                        placeholder="sk-...",
                        type="password",
                        value=TaxAppState.openai_api_key,
                        on_change=TaxAppState.set_api_key,
                        background="rgba(30, 41, 59, 0.5)",
                        border=f"1px solid {COLORS['border']}",
                        color="white",
                        padding="12px",
                        border_radius="8px",
                        width="100%",
                    ),
                    width="100%",
                    spacing="3",
                ),
                width="100%",
            ),
            
            # Filing Options
            mercury_card(
                rx.vstack(
                    rx.text("Filing Options", color="white", font_size="18px", font_weight="500"),
                    rx.divider(border_color=COLORS["border"]),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Filing Status", color=COLORS["text_secondary"], font_size="14px"),
                            rx.select(
                                ["single", "married_filing_jointly", "married_filing_separately", 
                                 "head_of_household", "qualifying_widow"],
                                value=TaxAppState.filing_status,
                                on_change=TaxAppState.set_filing_status,
                                width="200px",
                            ),
                            align_items="start",
                        ),
                        rx.vstack(
                            rx.text("Tax Year", color=COLORS["text_secondary"], font_size="14px"),
                            rx.select(
                                ["2024", "2025"],
                                value=str(TaxAppState.tax_year),
                                width="120px",
                            ),
                            align_items="start",
                        ),
                        spacing="6",
                    ),
                    width="100%",
                    spacing="3",
                ),
                width="100%",
                margin_top="24px",
            ),
            
            # Danger Zone
            mercury_card(
                rx.vstack(
                    rx.text("Danger Zone", color=COLORS["error"], font_size="18px", font_weight="500"),
                    rx.divider(border_color=COLORS["border"]),
                    rx.hstack(
                        rx.vstack(
                            rx.text("Clear All Data", color="white", font_weight="500"),
                            rx.text("Delete all uploaded documents and tax data", 
                                    color=COLORS["text_muted"], font_size="13px"),
                            align_items="start",
                        ),
                        rx.spacer(),
                        rx.box(
                            rx.text("Clear All"),
                            background="rgba(239, 68, 68, 0.2)",
                            color=COLORS["error"],
                            padding="8px 16px",
                            border_radius="6px",
                            cursor="pointer",
                            on_click=TaxAppState.clear_all,
                            _hover={"background": "rgba(239, 68, 68, 0.3)"},
                        ),
                        width="100%",
                    ),
                    width="100%",
                    spacing="3",
                ),
                width="100%",
                margin_top="24px",
                border="1px solid rgba(239, 68, 68, 0.3)",
            ),
            
            rx.link(outline_button("← Back to Dashboard"), href="/", margin_top="24px"),
            
            width="100%",
            max_width="600px",
            margin="0 auto",
            padding="100px 40px 40px 40px",
        ),
    )


# ============== App Configuration ==============
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="blue",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    style={
        "font_family": "Inter, sans-serif",
    },
)

# Register pages
app.add_page(dashboard_page, route="/", title="AI Tax - Dashboard")
app.add_page(upload_page, route="/upload", title="AI Tax - Upload")
app.add_page(review_page, route="/review", title="AI Tax - Review")
app.add_page(settings_page, route="/settings", title="AI Tax - Settings")
