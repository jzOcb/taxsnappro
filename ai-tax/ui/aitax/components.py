"""
TaxForge - Reusable UI Components (Fintech Light Theme)
"""
import reflex as rx
from typing import Callable


# ============== Theme Colors (Fintech Light) ==============
COLORS = {
    # Backgrounds
    "bg_page": "#f8fafc",           # Very light gray page background
    "bg_card": "white",              # Pure white cards
    "bg_hover": "#f1f5f9",           # Hover state
    "bg_input": "#f8fafc",           # Input background
    
    # Text
    "text_primary": "#1e293b",       # Dark navy text
    "text_secondary": "#475569",     # Slate text
    "text_muted": "#64748b",         # Slate-500 (was #94a3b8, now more readable)
    
    # Borders
    "border": "#e2e8f0",             # Light border
    "border_focus": "#6366f1",       # Focus border (indigo)
    
    # Accents
    "accent_primary": "#6366f1",     # Indigo primary
    "accent_purple": "#8b5cf6",      # Purple gradient end
    "accent_light": "#eef2ff",       # Light indigo background
    
    # Status colors
    "success": "#10b981",
    "success_light": "#d1fae5",
    "warning": "#f59e0b",
    "warning_light": "#fef3c7",
    "error": "#ef4444",
    "error_light": "#fee2e2",
}


# ============== Base Components ==============
def fintech_card(*children, **props) -> rx.Component:
    """Fintech-style card with subtle shadow."""
    border = props.pop("border", f"1px solid {COLORS['border']}")
    padding = props.pop("padding", "24px")
    return rx.box(
        *children,
        background=COLORS["bg_card"],
        border=border,
        border_radius="16px",
        padding=padding,
        box_shadow="0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)",
        **props,
    )


# Keep mercury_card as alias for compatibility
def mercury_card(*children, **props) -> rx.Component:
    """Alias for fintech_card."""
    return fintech_card(*children, **props)


def gradient_button(text: str, icon: str = None, **props) -> rx.Component:
    """Primary gradient button (indigo to purple)."""
    children = []
    if icon:
        children.append(rx.icon(icon, size=16))
    children.append(rx.text(text))
    
    return rx.box(
        rx.hstack(*children, spacing="2", justify="center"),
        background=f"linear-gradient(135deg, {COLORS['accent_primary']} 0%, {COLORS['accent_purple']} 100%)",
        color="white",
        padding="12px 24px",
        border_radius="8px",
        cursor="pointer",
        font_weight="500",
        font_size="15px",
        _hover={
            "opacity": "0.9",
            "transform": "translateY(-1px)",
            "box_shadow": "0 4px 12px rgba(99, 102, 241, 0.4)",
        },
        transition="all 0.2s ease",
        **props,
    )


def outline_button(text: str, **props) -> rx.Component:
    """Secondary outline button."""
    return rx.box(
        rx.text(text),
        background="white",
        color=COLORS["text_primary"],
        border=f"1px solid {COLORS['border']}",
        padding="12px 24px",
        border_radius="8px",
        cursor="pointer",
        font_weight="500",
        font_size="15px",
        _hover={
            "background": COLORS["bg_hover"],
            "border_color": COLORS["text_muted"],
        },
        transition="all 0.2s ease",
        **props,
    )


def stat_card(label: str, value: str, icon: str, color: str) -> rx.Component:
    """Statistics card with icon."""
    return fintech_card(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icon, size=20, color=color),
                    background=f"rgba(99, 102, 241, 0.1)",
                    padding="10px",
                    border_radius="10px",
                ),
                rx.spacer(),
                spacing="2",
                width="100%",
            ),
            rx.text(value, color=COLORS["text_primary"], font_size="28px", font_weight="600"),
            rx.text(label, color=COLORS["text_muted"], font_size="14px"),
            align_items="start",
            spacing="2",
        ),
        min_width="180px",
        flex="1",
    )


def section_header(title: str, subtitle: str = None, action: rx.Component = None) -> rx.Component:
    """Section header with optional action button."""
    return rx.hstack(
        rx.vstack(
            rx.text(title, color=COLORS["text_primary"], font_size="18px", font_weight="600"),
            rx.cond(
                subtitle is not None,
                rx.text(subtitle, color=COLORS["text_muted"], font_size="14px"),
                rx.fragment(),
            ),
            align_items="start",
            spacing="1",
        ),
        rx.spacer(),
        rx.cond(action is not None, action, rx.fragment()),
        width="100%",
    )


def empty_state(icon: str, message: str, action_text: str = None, 
                action_href: str = None) -> rx.Component:
    """Empty state placeholder."""
    children = [
        rx.box(
            rx.icon(icon, size=48, color=COLORS["text_muted"]),
            background=COLORS["accent_light"],
            padding="24px",
            border_radius="50%",
        ),
        rx.text(message, color=COLORS["text_muted"], font_size="16px"),
    ]
    if action_text and action_href:
        children.append(
            rx.link(action_text, href=action_href, color=COLORS["accent_primary"], 
                    font_weight="500")
        )
    
    return rx.vstack(
        *children,
        align_items="center",
        padding="40px",
        spacing="4",
    )


def badge(text: str, color_scheme: str = "blue") -> rx.Component:
    """Status badge."""
    colors = {
        "blue": (COLORS["accent_primary"], COLORS["accent_light"]),
        "green": (COLORS["success"], COLORS["success_light"]),
        "yellow": ("#b45309", COLORS["warning_light"]),
        "red": (COLORS["error"], COLORS["error_light"]),
    }
    text_color, bg_color = colors.get(color_scheme, colors["blue"])
    
    return rx.box(
        rx.text(text, font_size="12px", font_weight="600"),
        background=bg_color,
        color=text_color,
        padding="4px 12px",
        border_radius="12px",
    )


def data_row(label: str, value: rx.Component) -> rx.Component:
    """Data display row."""
    return rx.hstack(
        rx.text(label, color=COLORS["text_muted"], font_size="14px"),
        rx.spacer(),
        value,
        width="100%",
        padding="8px 0",
    )


def input_field(label: str, placeholder: str = "", value: str = "",
                on_change: Callable = None, type: str = "text") -> rx.Component:
    """Styled input field."""
    return rx.vstack(
        rx.text(label, color=COLORS["text_secondary"], font_size="14px", font_weight="500"),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            type=type,
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
        align_items="start",
        spacing="2",
        width="100%",
    )


def select_field(label: str, options: list, value: str = "",
                 on_change: Callable = None) -> rx.Component:
    """Styled select field."""
    return rx.vstack(
        rx.text(label, color=COLORS["text_secondary"], font_size="14px", font_weight="500"),
        rx.select(
            options,
            value=value,
            on_change=on_change,
            background=COLORS["bg_input"],
            border=f"1px solid {COLORS['border']}",
            color=COLORS["text_primary"],
            padding="12px 16px",
            border_radius="8px",
            width="100%",
        ),
        align_items="start",
        spacing="2",
        width="100%",
    )


# ============== Document Components ==============
def document_card(doc: dict) -> rx.Component:
    """Document list item card."""
    return rx.hstack(
        rx.box(
            rx.icon("file-text", size=20, color=COLORS["accent_primary"]),
            background=COLORS["accent_light"],
            padding="10px",
            border_radius="8px",
        ),
        rx.vstack(
            rx.text(doc["name"], color=COLORS["text_primary"], font_size="14px", font_weight="500"),
            rx.text(doc["type"], color=COLORS["text_muted"], font_size="12px"),
            align_items="start",
            spacing="0",
        ),
        rx.spacer(),
        rx.cond(
            doc["status"] == "parsed",
            badge("Parsed", "green"),
            badge("Pending", "yellow"),
        ),
        width="100%",
        padding="16px",
        background=COLORS["bg_card"],
        border_radius="12px",
        border=f"1px solid {COLORS['border']}",
        _hover={"background": COLORS["bg_hover"]},
        transition="all 0.15s ease",
    )


def w2_card(w2: dict, index: int, on_remove: Callable) -> rx.Component:
    """W-2 summary card."""
    return rx.hstack(
        rx.vstack(
            rx.text(w2["employer_name"], color=COLORS["text_primary"], font_weight="500"),
            rx.hstack(
                rx.text("Wages:", color=COLORS["text_muted"], font_size="13px"),
                rx.text(f"${w2['wages']:,.2f}", color=COLORS["success"], font_size="13px", font_weight="500"),
                rx.text("| Withheld:", color=COLORS["text_muted"], font_size="13px"),
                rx.text(f"${w2['federal_withheld']:,.2f}", color=COLORS["accent_primary"], font_size="13px", font_weight="500"),
                spacing="2",
            ),
            align_items="start",
            spacing="1",
        ),
        rx.spacer(),
        rx.icon(
            "trash-2", 
            size=16, 
            color=COLORS["error"],
            cursor="pointer",
            on_click=lambda: on_remove(index),
            _hover={"opacity": "0.7"},
        ),
        width="100%",
        padding="16px",
        background=COLORS["bg_card"],
        border_radius="12px",
        border=f"1px solid {COLORS['border']}",
    )


def income_1099_card(form: dict, index: int, on_remove: Callable) -> rx.Component:
    """1099 summary card."""
    return rx.hstack(
        rx.vstack(
            rx.hstack(
                badge(form["form_type"], "blue"),
                rx.text(form["payer_name"], color=COLORS["text_primary"], font_weight="500"),
                spacing="2",
            ),
            rx.text(f"${form['amount']:,.2f}", color=COLORS["success"], font_size="14px", font_weight="500"),
            align_items="start",
            spacing="1",
        ),
        rx.spacer(),
        rx.icon(
            "trash-2", 
            size=16, 
            color=COLORS["error"],
            cursor="pointer",
            on_click=lambda: on_remove(index),
            _hover={"opacity": "0.7"},
        ),
        width="100%",
        padding="16px",
        background=COLORS["bg_card"],
        border_radius="12px",
        border=f"1px solid {COLORS['border']}",
    )


# ============== Navigation ==============
def nav_bar() -> rx.Component:
    """Top navigation bar."""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.text("🔨", font_size="24px"),
                rx.text("TaxForge", color=COLORS["text_primary"], font_size="20px", font_weight="700"),
                spacing="2",
            ),
            rx.spacer(),
            rx.hstack(
                rx.link("Dashboard", href="/", color=COLORS["text_secondary"], font_weight="500",
                        _hover={"color": COLORS["accent_primary"]}),
                rx.link("Upload", href="/upload", color=COLORS["text_secondary"], font_weight="500",
                        _hover={"color": COLORS["accent_primary"]}),
                rx.link("Review", href="/review", color=COLORS["text_secondary"], font_weight="500",
                        _hover={"color": COLORS["accent_primary"]}),
                rx.link("Settings", href="/settings", color=COLORS["text_secondary"], font_weight="500",
                        _hover={"color": COLORS["accent_primary"]}),
                spacing="6",
            ),
            width="100%",
            max_width="1200px",
            margin="0 auto",
            padding="20px 40px",
        ),
        background="rgba(255, 255, 255, 0.95)",
        border_bottom=f"1px solid {COLORS['border']}",
        backdrop_filter="blur(10px)",
        position="fixed",
        top="0",
        left="0",
        right="0",
        z_index="100",
    )


def page_container(*children) -> rx.Component:
    """Page container with nav and proper padding."""
    return rx.box(
        nav_bar(),
        rx.box(
            *children,
            min_height="100vh",
            background=COLORS["bg_page"],
        ),
    )


# ============== Modal / Dialog ==============
def api_key_modal(is_open: bool, on_close: Callable, api_key_value: str, 
                  on_api_key_change: Callable, on_save: Callable) -> rx.Component:
    """API key configuration modal."""
    return rx.cond(
        is_open,
        rx.box(
            # Backdrop
            rx.box(
                position="fixed",
                top="0",
                left="0",
                right="0",
                bottom="0",
                background="rgba(0,0,0,0.5)",
                z_index="200",
                on_click=on_close,
            ),
            # Modal content
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.hstack(
                            rx.icon("key", size=24, color=COLORS["accent_primary"]),
                            rx.text("Configure API Key", color=COLORS["text_primary"], 
                                   font_size="20px", font_weight="600"),
                            spacing="3",
                        ),
                        rx.spacer(),
                        rx.icon("x", size=20, color=COLORS["text_muted"], cursor="pointer",
                               on_click=on_close, _hover={"color": COLORS["text_primary"]}),
                        width="100%",
                    ),
                    
                    # Body
                    rx.box(
                        rx.vstack(
                            rx.box(
                                rx.hstack(
                                    rx.icon("circle-alert", size=16, color=COLORS["warning"]),
                                    rx.text("API key required for document parsing", 
                                           color="#b45309", font_size="14px", font_weight="500"),
                                    spacing="2",
                                ),
                                background=COLORS["warning_light"],
                                padding="12px 16px",
                                border_radius="8px",
                                width="100%",
                            ),
                            rx.text(
                                "TaxForge uses Google Gemini (FREE) to extract data from your tax documents. "
                                "Get your API key in 30 seconds:",
                                color=COLORS["text_secondary"],
                                font_size="14px",
                                line_height="1.6",
                            ),
                            rx.vstack(
                                rx.hstack(
                                    rx.box(
                                        rx.text("1", font_size="12px", font_weight="600", color="white"),
                                        background=COLORS["accent_primary"],
                                        padding="4px 10px",
                                        border_radius="50%",
                                    ),
                                    rx.text("Go to ", color=COLORS["text_secondary"], font_size="14px"),
                                    rx.link(
                                        "aistudio.google.com/apikey",
                                        href="https://aistudio.google.com/apikey",
                                        color=COLORS["accent_primary"],
                                        font_weight="500",
                                        is_external=True,
                                    ),
                                    spacing="2",
                                ),
                                rx.hstack(
                                    rx.box(
                                        rx.text("2", font_size="12px", font_weight="600", color="white"),
                                        background=COLORS["accent_primary"],
                                        padding="4px 10px",
                                        border_radius="50%",
                                    ),
                                    rx.text("Sign in with Google and click 'Create API Key'", 
                                           color=COLORS["text_secondary"], font_size="14px"),
                                    spacing="2",
                                ),
                                rx.hstack(
                                    rx.box(
                                        rx.text("3", font_size="12px", font_weight="600", color="white"),
                                        background=COLORS["accent_primary"],
                                        padding="4px 10px",
                                        border_radius="50%",
                                    ),
                                    rx.text("Copy and paste your key below", 
                                           color=COLORS["text_secondary"], font_size="14px"),
                                    spacing="2",
                                ),
                                spacing="3",
                                align_items="start",
                                padding="8px 0",
                            ),
                            rx.vstack(
                                rx.text("Gemini API Key", color=COLORS["text_secondary"], 
                                       font_size="14px", font_weight="500"),
                                rx.input(
                                    placeholder="AIza...",
                                    type="password",
                                    value=api_key_value,
                                    on_change=on_api_key_change,
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
                            rx.hstack(
                                rx.icon("circle-check", size=14, color=COLORS["success"]),
                                rx.text("FREE: 1,500 requests/day — more than enough!", 
                                       color=COLORS["success"], font_size="13px", font_weight="500"),
                                spacing="2",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        padding="16px 0",
                        width="100%",
                    ),
                    
                    # Footer
                    rx.hstack(
                        rx.spacer(),
                        outline_button("Cancel", on_click=on_close),
                        gradient_button("Save & Continue", on_click=on_save),
                        spacing="3",
                        width="100%",
                        padding_top="8px",
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
                background="white",
                border_radius="16px",
                padding="24px",
                box_shadow="0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="201",
                width="90%",
                max_width="480px",
            ),
        ),
    )


def processing_overlay(
    is_processing: bool,
    current_file: str,
    file_index: int,
    total_files: int,
) -> rx.Component:
    """Full-screen processing overlay with progress."""
    return rx.cond(
        is_processing,
        rx.box(
            # Backdrop
            rx.box(
                position="fixed",
                top="0",
                left="0",
                right="0",
                bottom="0",
                background="rgba(0, 0, 0, 0.5)",
                z_index="300",
            ),
            # Modal
            rx.box(
                rx.vstack(
                    rx.box(
                        rx.spinner(size="3", color=COLORS["accent_primary"]),
                        padding="16px",
                        background=COLORS["accent_light"],
                        border_radius="50%",
                    ),
                    rx.text("Processing Documents", 
                            color=COLORS["text_primary"],
                            font_size="20px", 
                            font_weight="600"),
                    rx.text(f"File {file_index} of {total_files}",
                            color=COLORS["text_secondary"],
                            font_size="14px"),
                    rx.text(current_file,
                            color=COLORS["accent_primary"],
                            font_size="14px",
                            font_weight="500",
                            max_width="280px",
                            overflow="hidden",
                            text_overflow="ellipsis",
                            white_space="nowrap"),
                    rx.box(
                        rx.progress(
                            value=file_index,
                            max=total_files,
                            width="100%",
                            color_scheme="indigo",
                        ),
                        width="100%",
                        padding="8px 0",
                    ),
                    rx.text("Please wait while AI extracts data...",
                            color=COLORS["text_muted"],
                            font_size="13px"),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                background="white",
                border_radius="16px",
                padding="32px",
                box_shadow="0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="301",
                width="90%",
                max_width="360px",
                text_align="center",
            ),
        ),
    )
