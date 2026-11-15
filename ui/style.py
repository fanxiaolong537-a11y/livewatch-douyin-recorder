"""Shared colors and controls for the desktop interface."""

import flet as ft

INK = '#1D1D1F'
MUTED = '#6E6E73'
BLUE = '#0068DA'
BLUE_WASH = '#E3EEFC'
GREEN = '#167344'
BG = '#F5F5F7'
SIDEBAR = '#EDEDF0'
PAPER = '#FFFFFF'
LINE = '#E2E2E7'
RED = '#AC382F'

PAGES = (
    ('直播监控', ft.Icons.LIVE_TV, '跟踪主播的开播状态和录制进度'),
    ('录像管理', ft.Icons.VIDEO_LIBRARY, '查找、播放与管理本地录像'),
    ('数据统计', ft.Icons.BAR_CHART, '查看录制时长和存储用量'),
    ('软件设置', ft.Icons.SETTINGS, '管理录制参数、组件与诊断'),
)


def label(text, size=14, color=INK, *, weight=None, **kwargs):
    return ft.Text(str(text), size=size, color=color, weight=weight, **kwargs)


def heading(title, description, actions=None):
    copy = ft.Column(
        [label(title, 30, weight=ft.FontWeight.BOLD), label(description, 13, MUTED)],
        spacing=4,
    )
    if actions is None:
        return copy
    return ft.Row([copy, ft.Container(expand=True), actions], spacing=12)


def button(text, handler, primary=False, *, icon=None):
    return ft.Button(
        text, icon=icon, on_click=handler,
        style=ft.ButtonStyle(
            bgcolor=BLUE if primary else PAPER,
            color=PAPER if primary else BLUE,
            elevation=0,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            shape=ft.RoundedRectangleBorder(radius=9),
            side=ft.BorderSide(1, BLUE if primary else LINE),
        ),
    )


def panel(content, padding=20, *, expand=None):
    return ft.Container(
        content, padding=padding, bgcolor=PAPER, expand=expand,
        border=ft.Border.all(1, LINE), border_radius=16,
    )


def metric(title, value, icon, color=BLUE):
    return panel(ft.Column([
        ft.Container(ft.Icon(icon, size=17, color=color), padding=7,
                     bgcolor='#E8F5ED' if color == GREEN else BLUE_WASH, border_radius=9),
        label(value, 25, weight=ft.FontWeight.W_600),
        label(title, 12, MUTED),
    ], spacing=8), padding=16, expand=True)


def empty_state(icon, title, message, action=None):
    controls = [
        ft.Container(ft.Icon(icon, color=BLUE, size=24), padding=12,
                     bgcolor=BLUE_WASH, border_radius=14),
        label(title, 18, weight=ft.FontWeight.W_600),
        label(message, 13, MUTED, text_align=ft.TextAlign.CENTER),
    ]
    if action is not None:
        controls.append(action)
    return panel(ft.Column(controls, spacing=11,
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                 padding=36)


def status_badge(state, tooltip=None):
    if state in ('录制中', '直播中', '已开播') or state.endswith(' · 已就绪'):
        color, background = GREEN, '#E8F5ED'
    elif state in ('解析失败', '录制失败', '磁盘不足', '访问受限') or state.endswith(' · 缺失'):
        color, background = RED, '#FCECEB'
    elif state in ('正在重连', '等待录制'):
        color, background = '#805812', '#FFF1D6'
    else:
        color, background = MUTED, BG
    return ft.Container(label(state, 12, color), bgcolor=background,
                        border_radius=12, padding=ft.Padding.symmetric(horizontal=9, vertical=4),
                        tooltip=tooltip)


def table(headers, rows):
    grid = ft.DataTable(
        columns=[ft.DataColumn(label(h, 12, MUTED, weight=ft.FontWeight.W_600))
                 for h in headers],
        rows=rows, column_spacing=19, horizontal_margin=16, heading_row_height=42,
        data_row_min_height=63, data_row_max_height=76,
        heading_row_color='#F9F9FB', divider_thickness=1,
    )
    return panel(ft.Row([grid], scroll=ft.ScrollMode.AUTO), padding=1)


def cell(text):
    return ft.DataCell(label(text, 13))
