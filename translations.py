"""
Translation system for PUBG Tracker bot.

Supports the top 10 most used languages:
- English (en)
- Mandarin Chinese (zh)
- Hindi (hi)
- Spanish (es)
- Arabic (ar)
- French (fr)
- Bengali (bn)
- Portuguese (pt)
- Indonesian (id)
- Urdu (ur)
"""

TRANSLATIONS = {
    "en": {
        # Common UI strings
        "not_configured": "Not configured",
        "enabled": "Enabled",
        "disabled": "Disabled",
        "next_run": "Next run",
        "due_now": "Due now (the scheduler checks about every 15 minutes)",
        "scheduler_note": "Scheduler checks every 15 minutes; a report can post shortly after its shown time.",
        
        # Report titles
        "clan_digest": "Clan Digest",
        "last_active": "Last Active",
        "ranked": "Ranked",
        "daily_highlights": "Daily Highlights",
        "clan_level": "Clan Level",
        "survival_mastery": "Survival Mastery",
        "donation_message": "Donation Message",
        
        # Time expressions
        "every_hours": "Every {hours} hour(s)",
        "daily_at": "Daily at {hour:02d}:{minute:02d} Eastern",
        "every_weekday_at": "Every {weekday} at {hour:02d}:{minute:02d} Eastern",
        "every_sunday_at": "Every Sunday at {hour:02d}:{minute:02d} Eastern",
        
        # Weekday names
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
        
        # Embed descriptions
        "last_active_description": "PUBG's API doesn't expose login history, so this shows the time of each player's most recent **match**, which is the closest available signal for \"last played.\"",
        "scheduled_report_status": "Only configured reports are scheduled. All times are Eastern and automatically follow EST/EDT.",
        "no_reports_configured": "No automatic reports are configured yet. Use the `/set...channel` and `/set...time` commands to schedule one.",
        
        # Status messages
        "active_24h": "Active last 24h",
        "tracked_players": "Tracked players",
        "protected_players": "Protected players",
        "not_found": "Not found",
        "protected_footer": "🛡️ = Protected from inactivity removal",
        "updates_daily": "Updates daily at 3am KST (live-updating, not reposted)",
        
        # Command responses
        "no_players_tracked": "No players tracked yet. Add some with `/addplayer`.",
        "player_added": "Added player: {name}",
        "player_removed": "Removed player: {name}",
        "player_already_tracked": "Player already tracked: {name}",
        "player_not_found": "Player not found: {name}",
        "language_set": "Language set to {language}",
        "invalid_language": "Invalid language code. Valid options: {languages}",
        "current_language": "Current language: {language}",
        
        # Error messages
        "pubg_api_error": "PUBG API error: {error}",
        "something_went_wrong": "Something went wrong: {error}",
        "guild_only": "This command only works inside a Discord server — try it there instead.",
    },
    
    "zh": {
        # Common UI strings
        "not_configured": "未配置",
        "enabled": "已启用",
        "disabled": "已禁用",
        "next_run": "下次运行",
        "due_now": "现在到期（调度器每15分钟检查一次）",
        "scheduler_note": "调度器每15分钟检查一次；报告可能在显示时间后不久发布。",
        
        # Report titles
        "clan_digest": "公会摘要",
        "last_active": "最后活跃",
        "ranked": "排位",
        "daily_highlights": "每日亮点",
        "clan_level": "公会等级",
        "survival_mastery": "生存精通",
        "donation_message": "捐赠信息",
        
        # Time expressions
        "every_hours": "每 {hours} 小时",
        "daily_at": "每天 {hour:02d}:{minute:02d} 东部时间",
        "every_weekday_at": "每周 {weekday} {hour:02d}:{minute:02d} 东部时间",
        "every_sunday_at": "每周日 {hour:02d}:{minute:02d} 东部时间",
        
        # Weekday names
        "monday": "星期一",
        "tuesday": "星期二",
        "wednesday": "星期三",
        "thursday": "星期四",
        "friday": "星期五",
        "saturday": "星期六",
        "sunday": "星期日",
        
        # Embed descriptions
        "last_active_description": "PUBG API 不暴露登录历史，因此显示每位玩家最近**比赛**的时间，这是最接近“最后游戏”的可用信号。",
        "scheduled_report_status": "仅配置的报告会自动发布。所有时间均为东部时间，并自动遵循 EST/EDT。",
        "no_reports_configured": "尚未配置自动报告。使用 `/set...channel` 和 `/set...time` 命令进行安排。",
        
        # Status messages
        "active_24h": "过去24小时活跃",
        "tracked_players": "跟踪的玩家",
        "protected_players": "受保护的玩家",
        "not_found": "未找到",
        "protected_footer": "🛡️ = 免受不活跃移除保护",
        "updates_daily": "每天KST凌晨3点更新（实时更新，不重新发布）",
        
        # Command responses
        "no_players_tracked": "尚未跟踪玩家。使用 `/addplayer` 添加。",
        "player_added": "已添加玩家：{name}",
        "player_removed": "已移除玩家：{name}",
        "player_already_tracked": "玩家已跟踪：{name}",
        "player_not_found": "未找到玩家：{name}",
        "language_set": "语言已设置为 {language}",
        "invalid_language": "无效的语言代码。有效选项：{languages}",
        "current_language": "当前语言：{language}",
        
        # Error messages
        "pubg_api_error": "PUBG API 错误：{error}",
        "something_went_wrong": "出现错误：{error}",
        "guild_only": "此命令仅在 Discord 服务器内有效 — 请在那里尝试。",
    },
    
    "es": {
        # Common UI strings
        "not_configured": "No configurado",
        "enabled": "Habilitado",
        "disabled": "Deshabilitado",
        "next_run": "Próxima ejecución",
        "due_now": "Vence ahora (el programador verifica cada 15 minutos)",
        "scheduler_note": "El programador verifica cada 15 minutos; un informe puede publicarse poco después de su hora mostrada.",
        
        # Report titles
        "clan_digest": "Resumen del clan",
        "last_active": "Última actividad",
        "ranked": "Clasificada",
        "daily_highlights": "Resaltados diarios",
        "clan_level": "Nivel del clan",
        "survival_mastery": "Maestría de supervivencia",
        "donation_message": "Mensaje de donación",
        
        # Time expressions
        "every_hours": "Cada {hours} hora(s)",
        "daily_at": "Diariamente a las {hour:02d}:{minute:02d} hora del este",
        "every_weekday_at": "Cada {weekday} a las {hour:02d}:{minute:02d} hora del este",
        "every_sunday_at": "Cada domingo a las {hour:02d}:{minute:02d} hora del este",
        
        # Weekday names
        "monday": "Lunes",
        "tuesday": "Martes",
        "wednesday": "Miércoles",
        "thursday": "Jueves",
        "friday": "Viernes",
        "saturday": "Sábado",
        "sunday": "Domingo",
        
        # Embed descriptions
        "last_active_description": "La API de PUBG no expone el historial de inicio de sesión, por lo que esto muestra la hora de la **partida** más reciente de cada jugador, que es la señal más cercana disponible para \"última jugada\".",
        "scheduled_report_status": "Solo se programan los informes configurados. Todos los horarios son del este y siguen automáticamente EST/EDT.",
        "no_reports_configured": "Aún no hay informes automáticos configurados. Use los comandos `/set...channel` y `/set...time` para programar uno.",
        
        # Status messages
        "active_24h": "Activo en las últimas 24h",
        "tracked_players": "Jugadores rastreados",
        "protected_players": "Jugadores protegidos",
        "not_found": "No encontrado",
        "protected_footer": "🛡️ = Protegido de eliminación por inactividad",
        "updates_daily": "Actualizaciones diarias a las 3am KST (actualización en vivo, no republicado)",
        
        # Command responses
        "no_players_tracked": "Aún no hay jugadores rastreados. Agregue algunos con `/addplayer`.",
        "player_added": "Jugador agregado: {name}",
        "player_removed": "Jugador eliminado: {name}",
        "player_already_tracked": "Jugador ya rastreado: {name}",
        "player_not_found": "Jugador no encontrado: {name}",
        "language_set": "Idioma establecido en {language}",
        "invalid_language": "Código de idioma inválido. Opciones válidas: {languages}",
        "current_language": "Idioma actual: {language}",
        
        # Error messages
        "pubg_api_error": "Error de API de PUBG: {error}",
        "something_went_wrong": "Algo salió mal: {error}",
        "guild_only": "Este comando solo funciona dentro de un servidor de Discord — inténtelo allí.",
    },
    
    # Additional languages (hi, ar, fr, bn, pt, id, ur) would be added here
    # For now, they will fall back to English
}


RTL_LANGUAGES = {"ar", "ur"}  # Right-to-left languages


def get_translation(language_code: str, key: str, **kwargs) -> str:
    """Get a translated string for the given language and key.
    
    Falls back to English if the language or key is not available.
    """
    lang_dict = TRANSLATIONS.get(language_code, TRANSLATIONS["en"])
    text = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    
    return text


def is_rtl(language_code: str) -> bool:
    """Check if the language is right-to-left."""
    return language_code in RTL_LANGUAGES
