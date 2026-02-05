"""
AI Tax - Reusable UI Components (Mercury Style)
"""
import reflex as rx
from typing import Callable


# ============== Theme Colors ==============
COLORS = {
    "bg_dark": "#0f172a",
    "bg_card": "rgba(30, 41, 59, 0.8)",
    "border": "rgba(148, 163, 184, 0.1)",
    "text_primary": "white",
    "text_secondary": "rgba(148, 163, 184, 0.8)",
    "text_muted": "rgba(148, 163, 184, 0.6)",
    "accent_blue": "#3b82f6",
    "accent_purple": "#8b5cf6",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
}


# ============== Base Components ==============
def mercury_card(*children, **props) -> rx.Component:
    """Mercury-style card with glass effect."""
    # Allow border override
    border = props.pop("border", f"1px solid {COLORS['border']}")
    return rx.box(
        *children,
        background="linear-gradient(145deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
        border=border,
        border_radius="16px",
        padding="24px",
        backdrop_filter="blur(10px)",
        **props,
    )


def gradient_button(text: str, icon: str = None, **props) -> rx.Component:
    """Primary gradient button."""
    children = []
    if icon:
        children.append(rx.icon(icon, size=16))
    children.append(rx.text(text))
    
    return rx.box(
        rx.hstack(*children, spacing="2", justify="center"),
        background=f"linear-gradient(135deg, {COLORS['accent_blue']} 0%, {COLORS['accent_purple']} 100%)",
        color="white",
        padding="12px 20px",
        border_radius="8px",
        cursor="pointer",
        font_weight="500",
        _hover={"opacity": "0.9"},
        **props,
    )


def outline_button(text: str, **props) -> rx.Component:
    """Secondary outline button."""
    return rx.box(
        rx.text(text),
        background="transparent",
        color=COLORS["text_secondary"],
        border=f"1px solid {COLORS['border']}",
        padding="12px 20px",
        border_radius="8px",
        cursor="pointer",
        _hover={"border_color": COLORS["text_secondary"]},
        **props,
    )


def stat_card(label: str, value: str, icon: str, color: str) -> rx.Component:
    """Statistics card with icon."""
    return mercury_card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=20, color=color),
                rx.text(label, color=COLORS["text_secondary"], font_size="14px"),
                spacing="2",
            ),
            rx.text(value, color=color, font_size="28px", font_weight="600"),
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
            rx.text(title, color="white", font_size="18px", font_weight="500"),
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
        rx.icon(icon, size=48, color="rgba(148, 163, 184, 0.3)"),
        rx.text(message, color=COLORS["text_muted"]),
    ]
    if action_text and action_href:
        children.append(
            rx.link(action_text, href=action_href, color=COLORS["accent_blue"])
        )
    
    return rx.vstack(
        *children,
        align_items="center",
        padding="40px",
        spacing="3",
    )


def badge(text: str, color_scheme: str = "blue") -> rx.Component:
    """Status badge."""
    colors = {
        "blue": (COLORS["accent_blue"], f"rgba(59, 130, 246, 0.2)"),
        "green": (COLORS["success"], f"rgba(16, 185, 129, 0.2)"),
        "yellow": (COLORS["warning"], f"rgba(245, 158, 11, 0.2)"),
        "red": (COLORS["error"], f"rgba(239, 68, 68, 0.2)"),
    }
    text_color, bg_color = colors.get(color_scheme, colors["blue"])
    
    return rx.box(
        rx.text(text, font_size="12px", font_weight="500"),
        background=bg_color,
        color=text_color,
        padding="4px 12px",
        border_radius="12px",
    )


def data_row(label: str, value: rx.Component) -> rx.Component:
    """Data display row."""
    return rx.hstack(
        rx.text(label, color=COLORS["text_muted"]),
        rx.spacer(),
        value,
        width="100%",
    )


def input_field(label: str, placeholder: str = "", value: str = "",
                on_change: Callable = None, type: str = "text") -> rx.Component:
    """Styled input field."""
    return rx.vstack(
        rx.text(label, color=COLORS["text_secondary"], font_size="14px"),
        rx.input(
            placeholder=placeholder,
            value=value,
            on_change=on_change,
            type=type,
            background="rgba(30, 41, 59, 0.5)",
            border=f"1px solid {COLORS['border']}",
            color="white",
            padding="12px",
            border_radius="8px",
            width="100%",
            _focus={"border_color": COLORS["accent_blue"]},
        ),
        align_items="start",
        spacing="2",
        width="100%",
    )


def select_field(label: str, options: list, value: str = "",
                 on_change: Callable = None) -> rx.Component:
    """Styled select field."""
    return rx.vstack(
        rx.text(label, color=COLORS["text_secondary"], font_size="14px"),
        rx.select(
            options,
            value=value,
            on_change=on_change,
            background="rgba(30, 41, 59, 0.5)",
            border=f"1px solid {COLORS['border']}",
            color="white",
            padding="12px",
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
        rx.icon("file-text", size=20, color=COLORS["accent_blue"]),
        rx.vstack(
            rx.text(doc["name"], color="white", font_size="14px"),
            rx.text(doc["type"], color=COLORS["text_muted"], font_size="12px"),
            align_items="start",
            spacing="0",
        ),
        rx.spacer(),
        rx.cond(
            doc["status"] == "parsed",
            badge("parsed", "green"),
            badge("pending", "yellow"),
        ),
        width="100%",
        padding="12px 16px",
        background="rgba(30, 41, 59, 0.5)",
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
    )


def w2_card(w2: dict, index: int, on_remove: Callable) -> rx.Component:
    """W-2 summary card."""
    return rx.hstack(
        rx.vstack(
            rx.text(w2["employer_name"], color="white", font_weight="500"),
            rx.hstack(
                rx.text("Wages:", color=COLORS["text_muted"], font_size="13px"),
                rx.text(f"${w2['wages']:,.2f}", color=COLORS["success"], font_size="13px"),
                rx.text("| Withheld:", color=COLORS["text_muted"], font_size="13px"),
                rx.text(f"${w2['federal_withheld']:,.2f}", color=COLORS["accent_blue"], font_size="13px"),
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
        ),
        width="100%",
        padding="16px",
        background="rgba(30, 41, 59, 0.5)",
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
    )


def income_1099_card(form: dict, index: int, on_remove: Callable) -> rx.Component:
    """1099 summary card."""
    return rx.hstack(
        rx.vstack(
            rx.hstack(
                badge(form["form_type"], "blue"),
                rx.text(form["payer_name"], color="white", font_weight="500"),
                spacing="2",
            ),
            rx.text(f"${form['amount']:,.2f}", color=COLORS["success"], font_size="14px"),
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
        ),
        width="100%",
        padding="16px",
        background="rgba(30, 41, 59, 0.5)",
        border_radius="8px",
        border=f"1px solid {COLORS['border']}",
    )


# ============== Navigation ==============
def nav_bar() -> rx.Component:
    """Top navigation bar."""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.text("⚡", font_size="24px"),
                rx.text("AI Tax", color="white", font_size="20px", font_weight="600"),
                spacing="2",
            ),
            rx.spacer(),
            rx.hstack(
                rx.link("Dashboard", href="/", color=COLORS["text_secondary"], 
                        _hover={"color": "white"}),
                rx.link("Upload", href="/upload", color=COLORS["text_secondary"],
                        _hover={"color": "white"}),
                rx.link("Review", href="/review", color=COLORS["text_secondary"],
                        _hover={"color": "white"}),
                rx.link("Settings", href="/settings", color=COLORS["text_secondary"],
                        _hover={"color": "white"}),
                spacing="6",
            ),
            width="100%",
            padding="20px 40px",
        ),
        background="rgba(15, 23, 42, 0.8)",
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
            background=f"linear-gradient(180deg, {COLORS['bg_dark']} 0%, #1e293b 100%)",
        ),
    )
