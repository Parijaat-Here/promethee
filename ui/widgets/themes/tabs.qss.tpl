/* ============================================================================
   Prométhée — tabs.qss.tpl
   Template QSS pour les onglets. Variables : {token_name} → remplacées par ThemeManager.
   ============================================================================ */

QTabWidget::pane { border: none; background-color: __base_bg__; }
QTabBar { background-color: __tabs_bar_bg__; border-bottom: 1px solid __border__; }
QTabBar::tab {
    background-color: transparent; color: __tabs_tab_color__; border: none;
    border-right: 1px solid __border__; padding: 0px 16px;
    height: 42px; min-width: 140px; max-width: 220px; font-size: 13px;
}
QTabBar::tab:selected {
    background-color: __base_bg__; color: __text_primary__;
    font-weight: 600; border-bottom: 2px solid __accent__;
}
QTabBar::tab:hover:!selected {
    background-color: __tabs_tab_hover_bg__; color: __tabs_tab_hover_color__;
}
QTabBar::close-button       { subcontrol-position: right; margin: 4px; }
QTabBar::close-button:hover { background-color: __tabs_close_hover_bg__; border-radius: 3px; }
