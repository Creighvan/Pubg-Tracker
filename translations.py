"""
Translation system for PUBG Tracker bot.

Supports 10 languages:
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
        "daily_at": "Daily at {hour:02d}:{minute:02d} UTC",
        "every_weekday_at": "Every {weekday} at {hour:02d}:{minute:02d} UTC",
        "every_sunday_at": "Every Sunday at {hour:02d}:{minute:02d} UTC",
        
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
        "scheduled_report_status": "Only configured reports are scheduled. All times are in UTC.",
        "no_reports_configured": "No automatic reports are configured yet. Use the `/set...channel` and `/set...time` commands to schedule one.",
        
        # Status messages
        "active_24h": "Active last 24h",
        "tracked_players": "Tracked players",
        "protected_players": "Protected players",
        "not_found": "Not found",
        "protected_footer": "🛡️ = Protected from inactivity removal",
        "updates_daily": "Updates daily at 02:00 UTC (live-updating, not reposted)",
        
        # Last Active Report
        "last_active_report": "Last Active Report",
        "last_active_description": "PUBG's API doesn't expose login history, so this shows the time of each player's most recent match, which is the closest available signal for \"last played.\"",
        "players": "Players",
        "source_manual": " *(manual)*",
        "source_auto_count": " *(auto-count)*",
        "less_than_1_hour": "< 1 hour ago",
        "hours_ago": "{hours} hour(s) ago",
        "days_ago": "{days} day(s) ago",
        "no_recent_matches": "No recent matches found",
        
        # Clan Report
        "clan_report": "Clan Report",
        "tracked_players": "Tracked players",
        "total_kills": "Total kills",
        "total_wins": "Total wins",
        "win_rate": "Win rate",
        "total_damage": "Total damage",
        "total_matches": "Total matches",
        "top_fraggers": "Top Fraggers",
        "lifetime_stats_footer": "Stats from the official PUBG API · lifetime, per game mode",
        
        # Clan Level Report
        "clan_level_report": "Clan Level & Weekly Progress",
        "current_level": "Current Level",
        "members": "Members",
        "weekly_progress": "Weekly Progress",
        "first_snapshot": "This is the first clan snapshot. The next weekly report will show the level change.",
        "level_change": "Level change since last weekly report: **{change:+d}**",
        "member_change": " · Member change: **{change:+d}**",
        "important_note": "Important",
        "clan_level_note": "PUBG exposes the clan level and member count, but not the XP needed for the next level. Progress is therefore measured by the change in clan level between weekly reports.",
        "weekly_clan_progress_footer": "Weekly Clan Progress · Official PUBG API",
        
        # Ranked Report
        "ranked_report": "Ranked",
        "ranked_description": "Current-season competitive ranked standings.",
        "highest_ranked": "Highest Ranked",
        "ranked_this_season": "Ranked this season",
        "ranking": "Ranking",
        "no_ranked_matches": "No ranked matches",
        "no_ranked_description": "No tracked players have ranked matches in this queue this season.",
        "ranked_footer": "Updates daily at 04:30 UTC (live-updating, not reposted) · Stats from the official PUBG API · ranked, current season",
        
        # Daily Highlights Report
        "daily_highlights": "Daily Highlights",
        "fun_titles": "Fun Titles",
        "highlights_description": "Based on {count} player(s) who played since daily reset (02:00 UTC).",
        "no_recent_matches_available": "No recent matches available",
        "no_recent_matches_description": "PUBG match telemetry is only available for the last 14 days. {count} player(s) have older matches that can't be analyzed.",
        "no_matches_played": "No matches played",
        "no_matches_description": "Nobody on the roster played in this window.",
        "top_10": "Top 10",
        "kills_best_match": "kills (best match)",
        "dmg_best_match": "dmg (best match)",
        "human_bot_split": "human / {count} bot",
        "matches_count": "match(es)",
        "highlights_footer": "Updates daily at 02:00 UTC (live-updating, not reposted) · Stats from the official PUBG API · daily highlights, last 24 hours",
        
        # Chicken Dinner Report
        "chicken_dinner": "Chicken Dinner",
        "recent_squad_wins": "Recent squad wins (last 5 matches per player)",
        "no_wins_yet": "No squad wins yet today!",
        "total_wins_today": "Total wins today",
        "chicken_dinner_footer": "Updates every 15 minutes · Resets daily at 02:00 UTC · Stats from the official PUBG API",
        
        # Mastery Report
        "mastery_report": "Weapon & Survival Mastery",
        "mastery_description": "Each player's highest-level weapon and overall survival mastery.",
        "top_weapon_mastery": "Top Weapon Mastery",
        "top_survival_level": "Top Survival Level",
        "mastery": "Mastery",
        "kills": "kills",
        "survival": "Survival",
        
        # Survival Mastery Report
        "survival_mastery_report": "Survival Mastery by Tier",
        "survival_mastery_description": "Each player's survival mastery level, grouped by tier.",
        "no_survival_data": "No survival mastery data available.",
        
        # Leaderboard Report
        "leaderboard_report": "Leaderboard Results",
        "leaderboard_description": "Official PUBG leaderboard placement results for tracked players.",
        "no_leaderboard_results": "No tracked players found on the leaderboard.",
        
        # Report Status
        "report_status": "Scheduled Report Status",
        "report_status_description": "Only configured reports are scheduled. All times are UTC.",
        "no_reports_configured": "No automatic reports configured yet. Use `/set...channel` and `/set...time` commands to schedule one.",
        "channel": "Channel",
        "schedule": "Schedule",
        "next_run": "Next run",
        "status": "Status",
        "enabled_status": "Enabled",
        "disabled_status": "Disabled",
        
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
        "daily_at": "每天 {hour:02d}:{minute:02d} UTC",
        "every_weekday_at": "每周 {weekday} {hour:02d}:{minute:02d} UTC",
        "every_sunday_at": "每周日 {hour:02d}:{minute:02d} UTC",
        
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
        "scheduled_report_status": "仅配置的报告会自动发布。所有时间均为 UTC。",
        "no_reports_configured": "尚未配置自动报告。使用 `/set...channel` 和 `/set...time` 命令进行安排。",
        
        # Status messages
        "active_24h": "过去24小时活跃",
        "tracked_players": "跟踪的玩家",
        "protected_players": "受保护的玩家",
        "not_found": "未找到",
        "protected_footer": "🛡️ = 免受不活跃移除保护",
        "updates_daily": "每天UTC凌晨2点更新（实时更新，不重新发布）",
        
        # Last Active Report
        "last_active_report": "最后活跃报告",
        "last_active_description": "PUBG API 不暴露登录历史，因此显示每位玩家最近**比赛**的时间，这是最接近“最后游戏”的可用信号。",
        "players": "玩家",
        "source_manual": " *(手动)*",
        "source_auto_count": " *(自动计数)*",
        "less_than_1_hour": "小于1小时前",
        "hours_ago": "{hours}小时前",
        "days_ago": "{days}天前",
        "no_recent_matches": "未找到最近的比赛",
        
        # Clan Report
        "clan_report": "公会报告",
        "tracked_players": "跟踪的玩家",
        "total_kills": "总击杀",
        "total_wins": "总胜利",
        "win_rate": "胜率",
        "total_damage": "总伤害",
        "total_matches": "总比赛",
        "top_fraggers": "顶级击杀者",
        "lifetime_stats_footer": "来自官方PUBG API的统计数据 · 终身，按游戏模式",
        
        # Clan Level Report
        "clan_level_report": "公会等级和每周进度",
        "current_level": "当前等级",
        "members": "成员",
        "weekly_progress": "每周进度",
        "first_snapshot": "这是第一次公会快照。下周报告将显示等级变化。",
        "level_change": "自上周报告以来的等级变化：**{change:+d}**",
        "member_change": " · 成员变化：**{change:+d}**",
        "important_note": "重要",
        "clan_level_note": "PUBG显示公会等级和成员数量，但不显示升级所需的经验值。因此，进度通过每周报告之间的公会等级变化来衡量。",
        "weekly_clan_progress_footer": "每周公会进度 · 官方PUBG API",
        
        # Ranked Report
        "ranked_report": "排位",
        "ranked_description": "当前赛季竞技排位排名。",
        "highest_ranked": "最高排名",
        "ranked_this_season": "本赛季排名",
        "ranking": "排名",
        "no_ranked_matches": "无排位比赛",
        "no_ranked_description": "没有跟踪的玩家在此队列的本赛季排位比赛。",
        "ranked_footer": "每天UTC凌晨4:30更新（实时更新，不重新发布） · 来自官方PUBG API的统计数据 · 排位，当前赛季",
        
        # Daily Highlights Report
        "daily_highlights": "每日亮点",
        "fun_titles": "趣味称号",
        "highlights_description": "基于{count}名自每日重置（UTC凌晨2点）以来玩的玩家。",
        "no_recent_matches_available": "无最近比赛可用",
        "no_recent_matches_description": "PUBG比赛遥测数据仅可用14天。{count}名玩家有无法分析的旧比赛。",
        "no_matches_played": "无比赛",
        "no_matches_description": "名册上没人在这个窗口内玩过。",
        "top_10": "前10名",
        "kills_best_match": "击杀（最佳比赛）",
        "dmg_best_match": "伤害（最佳比赛）",
        "human_bot_split": "人类 / {count} 机器人",
        "matches_count": "比赛",
        "highlights_footer": "每天UTC凌晨2点更新（实时更新，不重新发布） · 来自官方PUBG API的统计数据 · 每日亮点，过去24小时",
        
        # Chicken Dinner Report
        "chicken_dinner": "吃鸡",
        "recent_squad_wins": "最近小队胜利（每位玩家最近5场比赛）",
        "no_wins_yet": "今天还没有小队胜利！",
        "total_wins_today": "今天总胜利",
        "chicken_dinner_footer": "每15分钟更新 · 每天UTC凌晨4点重置 · 来自官方PUBG API的统计数据",
        
        # Mastery Report
        "mastery_report": "武器和生存精通",
        "mastery_description": "每位玩家的最高级武器和整体生存精通。",
        "top_weapon_mastery": "顶级武器精通",
        "top_survival_level": "顶级生存等级",
        "mastery": "精通",
        "kills": "击杀",
        "survival": "生存",
        
        # Survival Mastery Report
        "survival_mastery_report": "按等级分组的生存精通",
        "survival_mastery_description": "每位玩家的生存精通等级，按等级分组。",
        "no_survival_data": "没有生存精通数据可用。",
        
        # Leaderboard Report
        "leaderboard_report": "排行榜结果",
        "leaderboard_description": "跟踪玩家的官方PUBG排行榜定位结果。",
        "no_leaderboard_results": "没有跟踪的玩家在排行榜上找到。",
        
        # Report Status
        "report_status": "预定报告状态",
        "report_status_description": "仅配置的报告会自动发布。所有时间均为UTC。",
        "no_reports_configured": "尚未配置自动报告。使用 `/set...channel` 和 `/set...time` 命令进行安排。",
        "channel": "频道",
        "schedule": "时间表",
        "next_run": "下次运行",
        "status": "状态",
        "enabled_status": "已启用",
        "disabled_status": "已禁用",
        
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
        "scheduled_report_status": "Solo se programan los informes configurados. Todos los horarios son en UTC.",
        "no_reports_configured": "Aún no hay informes automáticos configurados. Use los comandos `/set...channel` y `/set...time` para programar uno.",
        
        # Status messages
        "active_24h": "Activo en las últimas 24h",
        "tracked_players": "Jugadores rastreados",
        "protected_players": "Jugadores protegidos",
        "not_found": "No encontrado",
        "protected_footer": "🛡️ = Protegido de eliminación por inactividad",
        "updates_daily": "Actualizaciones diarias a las 02:00 UTC (actualización en vivo, no republicado)",
        
        # Last Active Report
        "last_active_report": "Informe de última actividad",
        "last_active_description": "La API de PUBG no expone el historial de inicio de sesión, por lo que esto muestra la hora de la **partida** más reciente de cada jugador, que es la señal más cercana disponible para \"última jugada\".",
        "players": "Jugadores",
        "source_manual": " *(manual)*",
        "source_auto_count": " *(auto-contador)*",
        "less_than_1_hour": "Hace menos de 1 hora",
        "hours_ago": "Hace {hours} hora(s)",
        "days_ago": "Hace {days} día(s)",
        "no_recent_matches": "No se encontraron partidas recientes",
        
        # Clan Report
        "clan_report": "Informe del clan",
        "tracked_players": "Jugadores rastreados",
        "total_kills": "Total de bajas",
        "total_wins": "Total de victorias",
        "win_rate": "Tasa de victoria",
        "total_damage": "Daño total",
        "total_matches": "Total de partidas",
        "top_fraggers": "Mejores eliminadores",
        "lifetime_stats_footer": "Estadísticas de la API oficial de PUBG · toda la vida, por modo de juego",
        
        # Clan Level Report
        "clan_level_report": "Nivel del clan y progreso semanal",
        "current_level": "Nivel actual",
        "members": "Miembros",
        "weekly_progress": "Progreso semanal",
        "first_snapshot": "Esta es la primera instantánea del clan. El próximo informe semanal mostrará el cambio de nivel.",
        "level_change": "Cambio de nivel desde el último informe semanal: **{change:+d}**",
        "member_change": " · Cambio de miembros: **{change:+d}**",
        "important_note": "Importante",
        "clan_level_note": "PUBG expone el nivel del clan y el número de miembros, pero no la XP necesaria para el siguiente nivel. Por lo tanto, el progreso se mide por el cambio en el nivel del clan entre informes semanales.",
        "weekly_clan_progress_footer": "Progreso semanal del clan · API oficial de PUBG",
        
        # Ranked Report
        "ranked_report": "Clasificada",
        "ranked_description": "Clasificación competitiva de la temporada actual.",
        "highest_ranked": "Clasificación más alta",
        "ranked_this_season": "Clasificados esta temporada",
        "ranking": "Clasificación",
        "no_ranked_matches": "Sin partidas clasificadas",
        "no_ranked_description": "Ningún jugador rastreado tiene partidas clasificadas en esta cola esta temporada.",
        "ranked_footer": "Actualizaciones diarias a las 04:30 UTC (actualización en vivo, no republicado) · Estadísticas de la API oficial de PUBG · clasificada, temporada actual",
        
        # Chicken Dinner Report
        "chicken_dinner": "Pollo al horno",
        "recent_squad_wins": "Victorias recientes de escuadrón (últimas 5 partidas por jugador)",
        "no_wins_yet": "Aún no hay victorias de escuadrón hoy!",
        "total_wins_today": "Victorias totales hoy",
        "chicken_dinner_footer": "Actualizaciones cada 15 minutos · Restablecimiento diario a las 02:00 UTC · Estadísticas de la API oficial de PUBG",
        
        # Mastery Report
        "mastery_report": "Maestría de armas y supervivencia",
        "mastery_description": "La maestría de arma de mayor nivel y la maestría de supervivencia general de cada jugador.",
        "top_weapon_mastery": "Mejor maestría de arma",
        "top_survival_level": "Mejor nivel de supervivencia",
        "mastery": "Maestría",
        "kills": "bajas",
        "survival": "Supervivencia",
        
        # Survival Mastery Report
        "survival_mastery_report": "Maestría de supervivencia por nivel",
        "survival_mastery_description": "Nivel de maestría de supervivencia de cada jugador, agrupado por nivel.",
        "no_survival_data": "No hay datos de maestría de supervivencia disponibles.",
        
        # Leaderboard Report
        "leaderboard_report": "Resultados de la tabla de clasificación",
        "leaderboard_description": "Resultados de clasificación oficial de PUBG para jugadores rastreados.",
        "no_leaderboard_results": "No se encontraron jugadores rastreados en la tabla de clasificación.",
        
        # Report Status
        "report_status": "Estado del informe programado",
        "report_status_description": "Solo se programan los informes configurados. Todos los horarios son UTC.",
        "no_reports_configured": "Aún no hay informes automáticos configurados. Use los comandos `/set...channel` y `/set...time` para programar uno.",
        "channel": "Canal",
        "schedule": "Horario",
        "next_run": "Próxima ejecución",
        "status": "Estado",
        "enabled_status": "Habilitado",
        "disabled_status": "Deshabilitado",
        
        # Command responses
        "daily_highlights": "Resaltados diarios",
        "fun_titles": "Títulos divertidos",
        "highlights_description": "Basado en {count} jugador(es) que jugaron desde el restablecimiento diario (02:00 UTC).",
        "no_recent_matches_available": "No hay partidas recientes disponibles",
        "no_recent_matches_description": "La telemetría de partidas de PUBG solo está disponible durante los últimos 14 días. {count} jugador(es) tienen partidas más antiguas que no se pueden analizar.",
        "no_matches_played": "Sin partidas jugadas",
        "no_matches_description": "Nadie en la lista jugó en esta ventana.",
        "top_10": "Top 10",
        "kills_best_match": "bajas (mejor partida)",
        "dmg_best_match": "daño (mejor partida)",
        "human_bot_split": "humano / {count} bot",
        "matches_count": "partida(s)",
        "highlights_footer": "Actualizaciones diarias a las 02:00 UTC (actualización en vivo, no republicado) · Estadísticas de la API oficial de PUBG · resaltados diarios, últimas 24 horas",
        
        # Chicken Dinner Report
        "chicken_dinner": "Pollo al horno",
        "recent_squad_wins": "Victorias recientes de escuadrón (últimas 5 partidas por jugador)",
        "no_wins_yet": "¡Aún no hay victorias de escuadrón hoy!",
        "total_wins_today": "Victorias totales hoy",
        "chicken_dinner_footer": "Actualizaciones cada 15 minutos · Restablecimiento diario a las 02:00 UTC · Estadísticas de la API oficial de PUBG",
        
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
    
    "hi": {
        # Common UI strings
        "not_configured": "कॉन्फ़िगर नहीं",
        "enabled": "सक्षम",
        "disabled": "अक्षम",
        "next_run": "अगला रन",
        "due_now": "अभी देय (शेड्यूलर हर 15 मिनट में जांचता है)",
        "scheduler_note": "शेड्यूलर हर 15 मिनट में जांचता है; रिपोर्ट दिखाए गए समय के बाद जल्द ही पोस्ट हो सकती है।",
        
        # Report titles
        "clan_digest": "क्लान डाइजेस्ट",
        "last_active": "अंतिम सक्रिय",
        "ranked": "रैंक",
        "daily_highlights": "दैनिक हाइलाइट्स",
        "clan_level": "क्लान स्तर",
        "survival_mastery": "जीविता महारत",
        "donation_message": "दान संदेश",
        
        # Time expressions
        "every_hours": "हर {hours} घंटे",
        "daily_at": "दैनिक {hour:02d}:{minute:02d} पूर्वी समय",
        "every_weekday_at": "हर {weekday} {hour:02d}:{minute:02d} पूर्वी समय",
        "every_sunday_at": "हर रविवार {hour:02d}:{minute:02d} पूर्वी समय",
        
        # Weekday names
        "monday": "सोमवार",
        "tuesday": "मंगलवार",
        "wednesday": "बुधवार",
        "thursday": "गुरुवार",
        "friday": "शुक्रवार",
        "saturday": "शनिवार",
        "sunday": "रविवार",
        
        # Embed descriptions
        "last_active_description": "PUBG API लॉगिन इतिहास को उजागर नहीं करता, इसलिए यह प्रत्येक खिलाड़ी के सबसे हालिया **मैच** का समय दिखाता है, जो \"अंतिम खेला\" के लिए उपलब्ध सबसे करीबी संकेत है।",
        "scheduled_report_status": "केवल कॉन्फ़िगर किए गए रिपोर्ट शेड्यूल किए जाते हैं। सभी समय UTC में हैं।",
        "no_reports_configured": "अभी तक कोई स्वचालित रिपोर्ट कॉन्फ़िगर नहीं की गई है। एक को शेड्यूल करने के लिए `/set...channel` और `/set...time` कमांड का उपयोग करें।",
        
        # Status messages
        "active_24h": "पिछले 24 घंटे में सक्रिय",
        "tracked_players": "ट्रैक किए गए खिलाड़ी",
        "protected_players": "संरक्षित खिलाड़ी",
        "not_found": "नहीं मिला",
        "protected_footer": "🛡️ = निष्क्रियता हटाने से संरक्षित",
        "updates_daily": "दैनिक UTC रात 2 बजे अपडेट (लाइव अपडेट, पुनः पोस्ट नहीं)",
        
        # Last Active Report
        "last_active_report": "अंतिम सक्रिय रिपोर्ट",
        "last_active_description": "PUBG API लॉगिन इतिहास को उजागर नहीं करता, इसलिए यह प्रत्येक खिलाड़ी के सबसे हालिया **मैच** का समय दिखाता है, जो \"अंतिम खेला\" के लिए उपलब्ध सबसे करीबी संकेत है।",
        "players": "खिलाड़ी",
        "source_manual": " *(मैनुअल)*",
        "source_auto_count": " *(स्वचालित गणना)*",
        "less_than_1_hour": "1 घंटे से कम पहले",
        "hours_ago": "{hours} घंटे पहले",
        "days_ago": "{days} दिन पहले",
        "no_recent_matches": "हाल के मैच नहीं मिले",
        
        # Clan Report
        "clan_report": "क्लान रिपोर्ट",
        "tracked_players": "ट्रैक किए गए खिलाड़ी",
        "total_kills": "कुल किल",
        "total_wins": "कुल जीत",
        "win_rate": "जीत दर",
        "total_damage": "कुल नुकसान",
        "total_matches": "कुल मैच",
        "top_fraggers": "शीर्ष फ्रैगर्स",
        "lifetime_stats_footer": "आधिकारिक PUBG API से आँकड़े · जीवनकाल, प्रति गेम मोड",
        
        # Clan Level Report
        "clan_level_report": "क्लान स्तर और साप्ताहिक प्रगति",
        "current_level": "वर्तमान स्तर",
        "members": "सदस्य",
        "weekly_progress": "साप्ताहिक प्रगति",
        "first_snapshot": "यह पहला क्लान स्नैपशॉट है। अगला साप्ताहिक रिपोर्ट स्तर परिवर्तन दिखाएगा।",
        "level_change": "पिछले साप्ताहिक रिपोर्ट से स्तर परिवर्तन: **{change:+d}**",
        "member_change": " · सदस्य परिवर्तन: **{change:+d}**",
        "important_note": "महत्वपूर्ण",
        "clan_level_note": "PUBG क्लान स्तर और सदस्य संख्या को उजागर करता है, लेकिन अगले स्तर के लिए आवश्यक XP नहीं। इसलिए, प्रगति साप्ताहिक रिपोर्ट के बीच क्लान स्तर परिवर्तन से मापी जाती है।",
        "weekly_clan_progress_footer": "साप्ताहिक क्लान प्रगति · आधिकारिक PUBG API",
        
        # Ranked Report
        "ranked_report": "रैंक",
        "ranked_description": "वर्तमान सीज़न प्रतिस्पर्धात्मक रैंक्ड स्टैंडिंग्स।",
        "highest_ranked": "उच्चतम रैंक",
        "ranked_this_season": "इस सीज़न में रैंक किए गए",
        "ranking": "रैंकिंग",
        "no_ranked_matches": "कोई रैंक्ड मैच नहीं",
        "no_ranked_description": "इस कतार में इस सीज़न में कोई भी ट्रैक किए गए खिलाड़ी के पास रैंक्ड मैच नहीं हैं।",
        "ranked_footer": "दैनिक UTC रात 4:30 बजे अपडेट (लाइव अपडेट, पुनः पोस्ट नहीं) · आधिकारिक PUBG API से आँकड़े · रैंक्ड, वर्तमान सीज़न",
        
        # Daily Highlights Report
        "daily_highlights": "दैनिक हाइलाइट्स",
        "fun_titles": "मज़ेदार खिताब",
        "highlights_description": "दैनिक रीसेट (UTC रात 2 बजे) के बाद खेलने वाले {count} खिलाड़ी(यों) के आधार पर।",
        "no_recent_matches_available": "कोई हाल के मैच उपलब्ध नहीं",
        "no_recent_matches_description": "PUBG मैच टेलीमेट्री केवल पिछले 14 दिनों के लिए उपलब्ध है। {count} खिलाड़ी(यों) के पास पुराने मैच हैं जिनका विश्लेषण नहीं किया जा सकता।",
        "no_matches_played": "कोई मैच नहीं खेला",
        "no_matches_description": "रोस्टर पर किसी ने भी इस विंडो में नहीं खेला।",
        "top_10": "शीर्ष 10",
        "kills_best_match": "किल (सर्वश्रेष्ठ मैच)",
        "dmg_best_match": "नुकसान (सर्वश्रेष्ठ मैच)",
        "human_bot_split": "मानव / {count} बॉट",
        "matches_count": "मैच",
        "highlights_footer": "दैनिक UTC रात 2 बजे अपडेट (लाइव अपडेट, पुनः पोस्ट नहीं) · आधिकारिक PUBG API से आँकड़े · दैनिक हाइलाइट्स, पिछले 24 घंटे",
        
        # Chicken Dinner Report
        "chicken_dinner": "चिकन डिनर",
        "recent_squad_wins": "हाल के स्क्वाड जीत (प्रति खिलाड़ी पिछले 5 मैच)",
        "no_wins_yet": "आज तक कोई स्क्वाड जीत नहीं!",
        "total_wins_today": "आज कुल जीत",
        "chicken_dinner_footer": "दैनिक UTC रात 4 बजे रीसेट · आधिकारिक PUBG API से आँकड़े",
        
        # Mastery Report
        "mastery_report": "हथियार और जीविता महारत",
        "mastery_description": "प्रत्येक खिलाड़ी का उच्चतम स्तरीय हथियार और समग्र जीविता महारत।",
        "top_weapon_mastery": "शीर्ष हथियार महारत",
        "top_survival_level": "शीर्ष जीविता स्तर",
        "mastery": "महारत",
        "kills": "किल",
        "survival": "जीविता",
        
        # Survival Mastery Report
        "survival_mastery_report": "स्तर के अनुसार जीविता महारत",
        "survival_mastery_description": "प्रत्येक खिलाड़ी का जीविता महारत स्तर, स्तर के अनुसार समूहीकृत।",
        "no_survival_data": "कोई जीविता महारत डेटा उपलब्ध नहीं।",
        
        # Leaderboard Report
        "leaderboard_report": "लीडरबोर्ड परिणाम",
        "leaderboard_description": "ट्रैक किए गए खिलाड़ियों के लिए आधिकारिक PUBG लीडरबोर्ड प्लेसमेंट परिणाम।",
        "no_leaderboard_results": "लीडरबोर्ड पर कोई ट्रैक किए गए खिलाड़ी नहीं मिले।",
        
        # Report Status
        "report_status": "निर्धारित रिपोर्ट स्थिति",
        "report_status_description": "केवल कॉन्फ़िगर किए गए रिपोर्ट निर्धारित होते हैं। सभी समय UTC हैं।",
        "no_reports_configured": "अभी तक कोई स्वचालित रिपोर्ट कॉन्फ़िगर नहीं किया गया है। एक शेड्यूल करने के लिए `/set...channel` और `/set...time` कमांड का उपयोग करें।",
        "channel": "चैनल",
        "schedule": "समय सारणी",
        "next_run": "अगला रन",
        "status": "स्थिति",
        "enabled_status": "सक्षम",
        "disabled_status": "अक्षम",
        
        # Command responses
        "no_players_tracked": "अभी तक कोई खिलाड़ी ट्रैक नहीं किया गया। `/addplayer` के साथ कुछ जोड़ें।",
        "player_added": "खिलाड़ी जोड़ा गया: {name}",
        "player_removed": "खिलाड़ी हटाया गया: {name}",
        "player_already_tracked": "खिलाड़ी पहले से ट्रैक किया गया: {name}",
        "player_not_found": "खिलाड़ी नहीं मिला: {name}",
        "language_set": "भाषा {language} पर सेट की गई",
        "invalid_language": "अमान्य भाषा कोड। मान्य विकल्प: {languages}",
        "current_language": "वर्तमान भाषा: {language}",
        
        # Error messages
        "pubg_api_error": "PUBG API त्रुटि: {error}",
        "something_went_wrong": "कुछ गलत हो गया: {error}",
        "guild_only": "यह कमांड केवल Discord सर्वर के अंदर काम करता है — कृपया वहां आज़माएं।",
    },
    
    "ar": {
        # Common UI strings
        "not_configured": "غير مهيأ",
        "enabled": "ممكن",
        "disabled": "معطل",
        "next_run": "التشغيل التالي",
        "due_now": "مستحق الآن (يتحقق المجدول كل 15 دقيقة)",
        "scheduler_note": "يتحقق المجدول كل 15 دقيقة؛ يمكن نشر التقرير بعد وقت عرضه بقليل.",
        
        # Report titles
        "clan_digest": "ملخص العشيرة",
        "last_active": "آخر نشاط",
        "ranked": "مصنف",
        "daily_highlights": "أبرز اليومية",
        "clan_level": "مستوى العشيرة",
        "survival_mastery": "إتقان البقاء",
        "donation_message": "رسالة التبرع",
        
        # Time expressions
        "every_hours": "كل {hours} ساعة",
        "daily_at": "يومياً في {hour:02d}:{minute:02d} التوقيت الشرقي",
        "every_weekday_at": "كل {weekday} في {hour:02d}:{minute:02d} التوقيت الشرقي",
        "every_sunday_at": "كل يوم أحد في {hour:02d}:{minute:02d} التوقيت الشرقي",
        
        # Weekday names
        "monday": "الاثنين",
        "tuesday": "الثلاثاء",
        "wednesday": "الأربعاء",
        "thursday": "الخميس",
        "friday": "الجمعة",
        "saturday": "السبت",
        "sunday": "الأحد",
        
        # Embed descriptions
        "last_active_description": "واجهة برمجة تطبيقات PUBG لا تكشف عن سجل تسجيل الدخول، لذا يعرض هذا وقت آخر **مباراة** لكل لاعب، وهو أقرب إشارة متاحة لـ \"آخر لعبت\".",
        "scheduled_report_status": "يتم جدولة التقارير المهيأة فقط. جميع الأوقات بالتوقيت العالمي (UTC).",
        "no_reports_configured": "لم يتم تكوين أي تقارير تلقائية بعد. استخدم أوامر `/set...channel` و `/set...time` لجدولة واحدة.",
        
        # Status messages
        "active_24h": "نشط في آخر 24 ساعة",
        "tracked_players": "اللاعبون المتتبعون",
        "protected_players": "اللاعبون المحميون",
        "not_found": "غير موجود",
        "protected_footer": "🛡️ = محمي من الإزالة بسبب عدم النشاط",
        "updates_daily": "تحديثات يومية الساعة 02:00 UTC (تحديث مباشر، لا إعادة نشر)",
        
        # Last Active Report
        "last_active_report": "تقرير آخر نشاط",
        "last_active_description": "واجهة برمجة تطبيقات PUBG لا تكشف عن سجل تسجيل الدخول، لذا يعرض هذا وقت آخر **مباراة** لكل لاعب، وهو أقرب إشارة متاحة لـ \"آخر لعبت\".",
        "players": "اللاعبون",
        "source_manual": " *(يدوي)*",
        "source_auto_count": " *(عداد تلقائي)*",
        "less_than_1_hour": "أقل من ساعة",
        "hours_ago": "منذ {hours} ساعة",
        "days_ago": "منذ {days} يوم",
        "no_recent_matches": "لم يتم العثور على مباريات حديثة",
        
        # Clan Report
        "clan_report": "تقرير العشيرة",
        "tracked_players": "اللاعبون المتتبعون",
        "total_kills": "إجمالي القتل",
        "total_wins": "إجمالي الانتصارات",
        "win_rate": "معدل الفوز",
        "total_damage": "إجمالي الضرر",
        "total_matches": "إجمالي المباريات",
        "top_fraggers": "أفضل القتلة",
        "lifetime_stats_footer": "إحصائيات من واجهة برمجة تطبيقات PUBG الرسمية · مدى الحياة، حسب وضع اللعب",
        
        # Clan Level Report
        "clan_level_report": "مستوى العشيرة والتقدم الأسبوعي",
        "current_level": "المستوى الحالي",
        "members": "الأعضاء",
        "weekly_progress": "التقدم الأسبوعي",
        "first_snapshot": "هذه أول لقطة للعشيرة. التقرير الأسبوعي القادم سيظهر تغيير المستوى.",
        "level_change": "تغيير المستوى منذ آخر تقرير أسبوعي: **{change:+d}**",
        "member_change": " · تغيير الأعضاء: **{change:+d}**",
        "important_note": "مهم",
        "clan_level_note": "تكشف واجهة برمجة تطبيقات PUBG عن مستوى العشيرة وعدد الأعضاء، ولكن ليس XP المطلوب للمستوى التالي. لذلك، يتم قياس التقدم من خلال تغيير مستوى العشيرة بين التقارير الأسبوعية.",
        "weekly_clan_progress_footer": "التقدم الأسبوعي للعشيرة · واجهة برمجة تطبيقات PUBG الرسمية",
        
        # Ranked Report
        "ranked_report": "مصنف",
        "ranked_description": "تصنيفات تنافسية للموسم الحالي.",
        "highest_ranked": "أعلى تصنيف",
        "ranked_this_season": "مصنفون هذا الموسم",
        "ranking": "التصنيف",
        "no_ranked_matches": "لا توجد مباريات مصنفة",
        "no_ranked_description": "لا يوجد لاعبون متتبعون لديهم مباريات مصنفة في هذه الطابور هذا الموسم.",
        "ranked_footer": "تحديثات يومية الساعة 04:30 UTC (تحديث مباشر، لا إعادة نشر) · إحصائيات من واجهة برمجة تطبيقات PUBG الرسمية · مصنف، الموسم الحالي",
        
        # Daily Highlights Report
        "daily_highlights": "أبرز اليومية",
        "fun_titles": "عناوين ممتعة",
        "highlights_description": "بناءً على {count} لاعب(ون) لعبوا منذ إعادة التعيين اليومي (02:00 UTC).",
        "no_recent_matches_available": "لا توجد مباريات حديثة متاحة",
        "no_recent_matches_description": "تكون بيانات تتبع مباريات PUBG متاحة فقط لآخر 14 يومًا. {count} لاعب(ون) لديهم مباريات أقدم لا يمكن تحليلها.",
        "no_matches_played": "لم يتم لعب أي مباريات",
        "no_matches_description": "لم يلعب أحد في القائمة في هذه النافذة.",
        "top_10": "أفضل 10",
        "kills_best_match": "قتل (أفضل مباراة)",
        "dmg_best_match": "ضرر (أفضل مباراة)",
        "human_bot_split": "إنسان / {count} بوت",
        "matches_count": "مباراة(ات)",
        "highlights_footer": "تحديثات يومية الساعة 02:00 UTC (تحديث مباشر، لا إعادة نشر) · إحصائيات من واجهة برمجة تطبيقات PUBG الرسمية · أبرز اليومية، آخر 24 ساعة",
        
        # Chicken Dinner Report
        "chicken_dinner": "عشاء الدجاج",
        "recent_squad_wins": "انتصارات الفريق الأخيرة (آخر 5 مباريات لكل لاعب)",
        "no_wins_yet": "لا توجد انتصارات للفريق حتى الآن!",
        "total_wins_today": "إجمالي الانتصارات اليوم",
        "chicken_dinner_footer": "تحديثات كل 15 دقيقة · إعادة تعيين يومية الساعة 02:00 UTC · إحصائيات من واجهة برمجة تطبيقات PUBG الرسمية",
        
        # Mastery Report
        "mastery_report": "إتقان الأسلحة والبقاء",
        "mastery_description": "أعلى مستوى سلاح وإتقان البقاء الشامل لكل لاعب.",
        "top_weapon_mastery": "أعلى إتقان سلاح",
        "top_survival_level": "أعلى مستوى بقاء",
        "mastery": "إتقان",
        "kills": "قتل",
        "survival": "بقاء",
        
        # Survival Mastery Report
        "survival_mastery_report": "إتقان البقاء حسب المستوى",
        "survival_mastery_description": "مستوى إتقان البقاء لكل لاعب، مجمّع حسب المستوى.",
        "no_survival_data": "لا توجد بيانات إتقان البقاء متاحة.",
        
        # Leaderboard Report
        "leaderboard_report": "نتائج القائمة المتصدرين",
        "leaderboard_description": "نتائج تصنيف PUBG الرسمية للاعبين المتتبعين.",
        "no_leaderboard_results": "لم يتم العثور على لاعبين متتبعين في القائمة المتصدرين.",
        
        # Report Status
        "report_status": "حالة التقرير المجدول",
        "report_status_description": "يتم جدولة التقارير المهيأة فقط. جميع الأوقات هي UTC.",
        "no_reports_configured": "لم يتم تكوين أي تقارير تلقائية بعد. استخدم أوامر `/set...channel` و `/set...time` لجدولة واحدة.",
        "channel": "قناة",
        "schedule": "الجدول",
        "next_run": "التشغيل التالي",
        "status": "الحالة",
        "enabled_status": "ممكن",
        "disabled_status": "معطل",
        
        # Command responses
        "no_players_tracked": "لم يتم تتبع أي لاعبين بعد. أضف بعضًا باستخدام `/addplayer`.",
        "player_added": "تمت إضافة اللاعب: {name}",
        "player_removed": "تمت إزالة اللاعب: {name}",
        "player_already_tracked": "اللاعب متتبع بالفعل: {name}",
        "player_not_found": "اللاعب غير موجود: {name}",
        "language_set": "تم تعيين اللغة إلى {language}",
        "invalid_language": "رمز لغة غير صالح. الخيارات الصالحة: {languages}",
        "current_language": "اللغة الحالية: {language}",
        
        # Error messages
        "pubg_api_error": "خطأ في واجهة برمجة تطبيقات PUBG: {error}",
        "something_went_wrong": "حدث خطأ ما: {error}",
        "guild_only": "يعمل هذا الأمر فقط داخل خادم Discord — جربه هناك بدلاً من ذلك.",
    },
    
    "fr": {
        # Common UI strings
        "not_configured": "Non configuré",
        "enabled": "Activé",
        "disabled": "Désactivé",
        "next_run": "Prochaine exécution",
        "due_now": "Dû maintenant (le planificateur vérifie toutes les 15 minutes)",
        "scheduler_note": "Le planificateur vérifie toutes les 15 minutes; un rapport peut être publié peu après son heure affichée.",
        
        # Report titles
        "clan_digest": "Résumé du clan",
        "last_active": "Dernière activité",
        "ranked": "Classé",
        "daily_highlights": "Points forts quotidiens",
        "clan_level": "Niveau du clan",
        "survival_mastery": "Maîtrise de la survie",
        "donation_message": "Message de don",
        
        # Time expressions
        "every_hours": "Toutes les {hours} heure(s)",
        "daily_at": "Quotidien à {hour:02d}:{minute:02d} UTC",
        "every_weekday_at": "Chaque {weekday} à {hour:02d}:{minute:02d} UTC",
        "every_sunday_at": "Chaque dimanche à {hour:02d}:{minute:02d} UTC",
        
        # Weekday names
        "monday": "Lundi",
        "tuesday": "Mardi",
        "wednesday": "Mercredi",
        "thursday": "Jeudi",
        "friday": "Vendredi",
        "saturday": "Samedi",
        "sunday": "Dimanche",
        
        # Embed descriptions
        "last_active_description": "L'API PUBG n'expose pas l'historique de connexion, donc cela affiche l'heure du **match** le plus récent de chaque joueur, qui est le signal le plus proche disponible pour \"dernier joué\".",
        "scheduled_report_status": "Seuls les rapports configurés sont planifiés. Toutes les heures sont en UTC.",
        "no_reports_configured": "Aucun rapport automatique n'est encore configuré. Utilisez les commandes `/set...channel` et `/set...time` pour en planifier un.",
        
        # Status messages
        "active_24h": "Actif au cours des 24 dernières heures",
        "tracked_players": "Joueurs suivis",
        "protected_players": "Joueurs protégés",
        "not_found": "Non trouvé",
        "protected_footer": "🛡️ = Protégé de la suppression par inactivité",
        "updates_daily": "Mises à jour quotidiennes à 02:00 UTC (mise à jour en direct, non republié)",
        
        # Last Active Report
        "last_active_report": "Rapport de dernière activité",
        "last_active_description": "L'API PUBG n'expose pas l'historique de connexion, donc cela affiche l'heure du **match** le plus récent de chaque joueur, qui est le signal le plus proche disponible pour \"dernier joué\".",
        "players": "Joueurs",
        "source_manual": " *(manuel)*",
        "source_auto_count": " *(comptage auto)*",
        "less_than_1_hour": "Il y a moins d'1 heure",
        "hours_ago": "Il y a {hours} heure(s)",
        "days_ago": "Il y a {days} jour(s)",
        "no_recent_matches": "Aucune partie récente trouvée",
        
        # Clan Report
        "clan_report": "Rapport de clan",
        "tracked_players": "Joueurs suivis",
        "total_kills": "Total des éliminations",
        "total_wins": "Total des victoires",
        "win_rate": "Taux de victoire",
        "total_damage": "Dégâts totaux",
        "total_matches": "Total des parties",
        "top_fraggers": "Meilleurs éliminateurs",
        "lifetime_stats_footer": "Statistiques de l'API PUBG officielle · à vie, par mode de jeu",
        
        # Clan Level Report
        "clan_level_report": "Niveau de clan et progression hebdomadaire",
        "current_level": "Niveau actuel",
        "members": "Membres",
        "weekly_progress": "Progression hebdomadaire",
        "first_snapshot": "C'est la première capture de clan. Le prochain rapport hebdomadaire montrera le changement de niveau.",
        "level_change": "Changement de niveau depuis le dernier rapport hebdomadaire : **{change:+d}**",
        "member_change": " · Changement de membres : **{change:+d}**",
        "important_note": "Important",
        "clan_level_note": "PUBG expose le niveau de clan et le nombre de membres, mais pas l'XP nécessaire pour le niveau suivant. Par conséquent, la progression est mesurée par le changement de niveau de clan entre les rapports hebdomadaires.",
        "weekly_clan_progress_footer": "Progression hebdomadaire du clan · API PUBG officielle",
        
        # Ranked Report
        "ranked_report": "Classé",
        "ranked_description": "Classements compétitifs de la saison en cours.",
        "highest_ranked": "Classement le plus élevé",
        "ranked_this_season": "Classés cette saison",
        "ranking": "Classement",
        "no_ranked_matches": "Aucune partie classée",
        "no_ranked_description": "Aucun joueur suivi n'a de parties classées dans cette file cette saison.",
        "ranked_footer": "Mises à jour quotidiennes à 04:30 UTC (mise à jour en direct, non republié) · Statistiques de l'API PUBG officielle · classé, saison en cours",
        
        # Daily Highlights Report
        "daily_highlights": "Faits marquants quotidiens",
        "fun_titles": "Titres amusants",
        "highlights_description": "Basé sur {count} joueur(s) ayant joué depuis la réinitialisation quotidienne (02:00 UTC).",
        "no_recent_matches_available": "Aucune partie récente disponible",
        "no_recent_matches_description": "La télémétrie des parties PUBG n'est disponible que pendant les 14 derniers jours. {count} joueur(s) ont des parties plus anciennes qui ne peuvent pas être analysées.",
        "no_matches_played": "Aucune partie jouée",
        "no_matches_description": "Personne sur la liste n'a joué dans cette fenêtre.",
        "top_10": "Top 10",
        "kills_best_match": "éliminations (meilleure partie)",
        "dmg_best_match": "dégâts (meilleure partie)",
        "human_bot_split": "humain / {count} bot",
        "matches_count": "partie(s)",
        "highlights_footer": "Mises à jour quotidiennes à 02:00 UTC (mise à jour en direct, non republié) · Statistiques de l'API PUBG officielle · faits marquants quotidiens, dernières 24 heures",
        
        # Chicken Dinner Report
        "chicken_dinner": "Poulet rôti",
        "recent_squad_wins": "Victoires d'escouade récentes (5 dernières parties par joueur)",
        "no_wins_yet": "Aucune victoire d'escouade aujourd'hui !",
        "total_wins_today": "Victoires totales aujourd'hui",
        "chicken_dinner_footer": "Mises à jour toutes les 15 minutes · Réinitialisation quotidienne à 02:00 UTC · Statistiques de l'API PUBG officielle",
        
        # Mastery Report
        "mastery_report": "Maîtrise d'armes et de survie",
        "mastery_description": "La maîtrise d'arme de plus haut niveau et la maîtrise de survie globale de chaque joueur.",
        "top_weapon_mastery": "Meilleure maîtrise d'arme",
        "top_survival_level": "Meilleur niveau de survie",
        "mastery": "Maîtrise",
        "kills": "éliminations",
        "survival": "Survie",
        
        # Survival Mastery Report
        "survival_mastery_report": "Maîtrise de survie par niveau",
        "survival_mastery_description": "Niveau de maîtrise de survie de chaque joueur, groupé par niveau.",
        "no_survival_data": "Aucune donnée de maîtrise de survie disponible.",
        
        # Leaderboard Report
        "leaderboard_report": "Résultats du classement",
        "leaderboard_description": "Résultats de classement officiel PUBG pour les joueurs suivis.",
        "no_leaderboard_results": "Aucun joueur suivi trouvé dans le classement.",
        
        # Report Status
        "report_status": "État du rapport programmé",
        "report_status_description": "Seuls les rapports configurés sont programmés. Toutes les heures sont UTC.",
        "no_reports_configured": "Aucun rapport automatique n'est encore configuré. Utilisez les commandes `/set...channel` et `/set...time` pour en programmer un.",
        "channel": "Salon",
        "schedule": "Planning",
        "next_run": "Prochaine exécution",
        "status": "État",
        "enabled_status": "Activé",
        "disabled_status": "Désactivé",
        
        # Command responses
        "no_players_tracked": "Aucun joueur suivi pour le moment. Ajoutez-en avec `/addplayer`.",
        "player_added": "Joueur ajouté: {name}",
        "player_removed": "Joueur supprimé: {name}",
        "player_already_tracked": "Joueur déjà suivi: {name}",
        "player_not_found": "Joueur non trouvé: {name}",
        "language_set": "Langue définie sur {language}",
        "invalid_language": "Code de langue invalide. Options valides: {languages}",
        "current_language": "Langue actuelle: {language}",
        
        # Error messages
        "pubg_api_error": "Erreur de l'API PUBG: {error}",
        "something_went_wrong": "Une erreur s'est produite: {error}",
        "guild_only": "Cette commande ne fonctionne que dans un serveur Discord — essayez-la là-bas.",
    },
    
    "bn": {
        # Common UI strings
        "not_configured": "কনফিগার করা নেই",
        "enabled": "সক্ষম",
        "disabled": "অক্ষম",
        "next_run": "পরবর্তী রান",
        "due_now": "এখন দেয় (সময়সূচী প্রতি 15 মিনিটে পরীক্ষা করে)",
        "scheduler_note": "সময়সূচী প্রতি 15 মিনিটে পরীক্ষা করে; একটি রিপোর্ট তার প্রদর্শিত সময়ের পরে শীঘ্রই পোস্ট হতে পারে।",
        
        # Report titles
        "clan_digest": "ক্লান ডাইজেস্ট",
        "last_active": "শেষ সক্রিয়",
        "ranked": "র‍্যাঙ্কড",
        "daily_highlights": "দৈনিক হাইলাইটস",
        "clan_level": "ক্লান স্তর",
        "survival_mastery": "বেঁচে থাকার দক্ষতা",
        "donation_message": "দান বার্তা",
        
        # Time expressions
        "every_hours": "প্রতি {hours} ঘন্টা",
        "daily_at": "দৈনিক {hour:02d}:{minute:02d} UTC",
        "every_weekday_at": "প্রতি {weekday} {hour:02d}:{minute:02d} UTC",
        "every_sunday_at": "প্রতি রবিবার {hour:02d}:{minute:02d} UTC",
        
        # Weekday names
        "monday": "সোমবার",
        "tuesday": "মঙ্গলবার",
        "wednesday": "বুধবার",
        "thursday": "বৃহস্পতিবার",
        "friday": "শুক্রবার",
        "saturday": "শনিবার",
        "sunday": "রবিবার",
        
        # Embed descriptions
        "last_active_description": "PUBG API লগইন ইতিহাস প্রকাশ করে না, তাই এটি প্রতিটি খেলোয়াড়ের সবচেয়ে সাম্প্রতিক **ম্যাচ** এর সময় দেখায়, যা \"শেষ খেলা\" এর জন্য উপলব্ধ নিকটতম সংকেত।",
        "scheduled_report_status": "শুধুমাত্র কনফিগার করা রিপোর্টগুলি নির্ধারিত হয়। সমস্ত সময় UTC-এ।",
        "no_reports_configured": "এখনও কোনো স্বয়ংক্রিয় রিপোর্ট কনফিগার করা হয়নি। একটি নির্ধারণ করতে `/set...channel` এবং `/set...time` কমান্ড ব্যবহার করুন।",
        
        # Status messages
        "active_24h": "গত 24 ঘন্টায় সক্রিয়",
        "tracked_players": "ট্র্যাক করা খেলোয়াড়",
        "protected_players": "সুরক্ষিত খেলোয়াড়",
        "not_found": "পাওয়া যায়নি",
        "protected_footer": "🛡️ = নিষ্ক্রিয়তা অপসারণ থেকে সুরক্ষিত",
        "updates_daily": "দৈনিক UTC রাত 2 টায় আপডেট (লাইভ আপডেট, পুনঃপোস্ট নয়)",
        
        # Last Active Report
        "last_active_report": "শেষ সক্রিয় রিপোর্ট",
        "last_active_description": "PUBG API লগইন ইতিহাস প্রকাশ করে না, তাই এটি প্রতিটি খেলোয়াড়ের সবচেয়ে সাম্প্রতিক **ম্যাচ** এর সময় দেখায়, যা \"শেষ খেলা\" এর জন্য উপলব্ধ নিকটতম সংকেত।",
        "players": "খেলোয়াড়",
        "source_manual": " *(ম্যানুয়াল)*",
        "source_auto_count": " *(স্বয়ংক্রিয় গণনা)*",
        "less_than_1_hour": "1 ঘন্টার কম",
        "hours_ago": "{hours} ঘন্টা আগে",
        "days_ago": "{days} দিন আগে",
        "no_recent_matches": "সাম্প্রতিক ম্যাচ পাওয়া যায়নি",
        
        # Clan Report
        "clan_report": "ক্লান রিপোর্ট",
        "tracked_players": "ট্র্যাক করা খেলোয়াড়",
        "total_kills": "মোট কিল",
        "total_wins": "মোট জয়",
        "win_rate": "জয়ের হার",
        "total_damage": "মোট ক্ষতি",
        "total_matches": "মোট ম্যাচ",
        "top_fraggers": "শীর্ষ ফ্র্যাগার",
        "lifetime_stats_footer": "অফিসিয়াল PUBG API থেকে পরিসংখ্যান · আজীবন, প্রতি গেম মোড",
        
        # Clan Level Report
        "clan_level_report": "ক্লান লেভেল এবং সাপ্তাহিক অগ্রগতি",
        "current_level": "বর্তমান লেভেল",
        "members": "সদস্য",
        "weekly_progress": "সাপ্তাহিক অগ্রগতি",
        "first_snapshot": "এটি প্রথম ক্লান স্ন্যাপশট। পরবর্তী সাপ্তাহিক রিপোর্ট লেভেল পরিবর্তন দেখাবে।",
        "level_change": "শেষ সাপ্তাহিক রিপোর্ট থেকে লেভেল পরিবর্তন: **{change:+d}**",
        "member_change": " · সদস্য পরিবর্তন: **{change:+d}**",
        "important_note": "গুরুত্বপূর্ণ",
        "clan_level_note": "PUBG ক্লান লেভেল এবং সদস্য সংখ্যা প্রকাশ করে, কিন্তু পরবর্তী লেভেলের জন্য প্রয়োজনীয় XP নয়। তাই, অগ্রগতি সাপ্তাহিক রিপোর্টের মধ্যে ক্লান লেভেল পরিবর্তন দ্বারা পরিমাপ করা হয়।",
        "weekly_clan_progress_footer": "সাপ্তাহিক ক্লান অগ্রগতি · অফিসিয়াল PUBG API",
        
        # Ranked Report
        "ranked_report": "র‍্যাংকড",
        "ranked_description": "বর্তমান সিজন প্রতিযোগিতামূলক র‍্যাংকড স্ট্যান্ডিংস।",
        "highest_ranked": "সর্বোচ্চ র‍্যাংক",
        "ranked_this_season": "এই সিজনে র‍্যাংক করা",
        "ranking": "র‍্যাংকিং",
        "no_ranked_matches": "কোন র‍্যাংকড ম্যাচ নেই",
        "no_ranked_description": "এই সিজনে এই কিউতে কোন ট্র্যাক করা খেলোয়াড়ের র‍্যাংকড ম্যাচ নেই।",
        "ranked_footer": "দৈনিক UTC রাত 4:30 এ আপডেট (লাইভ আপডেট, পুনঃপোস্ট নয়) · অফিসিয়াল PUBG API থেকে পরিসংখ্যান · র‍্যাংকড, বর্তমান সিজন",
        
        # Daily Highlights Report
        "daily_highlights": "দৈনিক হাইলাইটস",
        "fun_titles": "মজার শিরোনাম",
        "highlights_description": "দৈনিক রিসেট (UTC রাত 2 টা) থেকে খেলা {count} খেলোয়াড়ের উপর ভিত্তি করে।",
        "no_recent_matches_available": "কোন সাম্প্রতিক ম্যাচ উপলব্ধ নেই",
        "no_recent_matches_description": "PUBG ম্যাচ টেলিমেট্রি শুধুমাত্র গত 14 দিনের জন্য উপলব্ধ। {count} খেলোয়াড়ের পুরানো ম্যাচ আছে যা বিশ্লেষণ করা যায় না।",
        "no_matches_played": "কোন ম্যাচ খেলা হয়নি",
        "no_matches_description": "রোস্টারে কেউ এই উইন্ডোতে খেলেনি।",
        "top_10": "শীর্ষ 10",
        "kills_best_match": "কিল (সেরা ম্যাচ)",
        "dmg_best_match": "ক্ষতি (সেরা ম্যাচ)",
        "human_bot_split": "মানব / {count} বট",
        "matches_count": "ম্যাচ",
        "highlights_footer": "দৈনিক UTC রাত 2 টা আপডেট (লাইভ আপডেট, পুনঃপোস্ট নয়) · অফিসিয়াল PUBG API থেকে পরিসংখ্যান · দৈনিক হাইলাইটস, গত 24 ঘন্টা",
        
        # Chicken Dinner Report
        "chicken_dinner": "চিকেন ডিনার",
        "recent_squad_wins": "সাম্প্রতিক স্কোয়াড জয় (প্রতি খেলোয়াড়ের শেষ 5 ম্যাচ)",
        "no_wins_yet": "আজ এখনও কোন স্কোয়াড জয় নেই!",
        "total_wins_today": "আজ মোট জয়",
        "chicken_dinner_footer": "প্রতি 15 মিনিটে আপডেট · দৈনিক UTC রাত 4 টা রিসেট · অফিসিয়াল PUBG API থেকে পরিসংখ্যান",
        
        # Mastery Report
        "mastery_report": "অস্ত্র এবং বেঁচে বাঁচ মাস্টারি",
        "mastery_description": "প্রত্যেক খেলোয়াড়ের সর্বোচ্চ স্তরের অস্ত্র এবং সামগ্রিক বেঁচে বাঁচ মাস্টারি।",
        "top_weapon_mastery": "শীর্ষ অস্ত্র মাস্টারি",
        "top_survival_level": "শীর্ষ বেঁচে বাঁচ স্তর",
        "mastery": "মাস্টারি",
        "kills": "কিল",
        "survival": "বেঁচে বাঁচ",
        
        # Survival Mastery Report
        "survival_mastery_report": "স্তর অনুযায় বেঁচে বাঁচ মাস্টারি",
        "survival_mastery_description": "প্রত্যেক খেলোয়াড়ের বেঁচে বাঁচ মাস্টারি স্তর, স্তর অনুযায় গ্রুপ করা।",
        "no_survival_data": "কোন বেঁচে বাঁচ মাস্টারি ডেটা উপলব্ধ নেই।",
        
        # Leaderboard Report
        "leaderboard_report": "লিডারবোর্ড ফলাফল",
        "leaderboard_description": "ট্র্যাক করা খেলোয়াড়দের জন্য অফিসিয়াল PUBG লিডারবোর্ড প্লেসমেন্ট ফলাফল।",
        "no_leaderboard_results": "লিডারবোর্ডে কোন ট্র্যাক করা খেলোয়াড় পাওয়া যায়নি।",
        
        # Report Status
        "report_status": "নির্ধারিত রিপোর্ট স্থিতি",
        "report_status_description": "শুধুমাত্র কনফিগার করা রিপোর্টগুলি নির্ধারিত হয়। সমস্ত সময UTC।",
        "no_reports_configured": "এখনও কোন স্বয়ংক্রিয় রিপোর্ট কনফিগার করা হয়নি। একট শিডিউল করতে `/set...channel` এবং `/set...time` কমান্ড ব্যবহার করুন।",
        "channel": "চ্যানেল",
        "schedule": "সময়সূচি",
        "next_run": "পরবর্তী রান",
        "status": "স্থিতি",
        "enabled_status": "সক্ষম",
        "disabled_status": "অক্ষম",
        
        # Command responses
        "no_players_tracked": "এখনও কোনো খেলোয়াড় ট্র্যাক করা হয়নি। `/addplayer` দিয়ে কিছু যোগ করুন।",
        "player_added": "খেলোয়াড় যোগ করা হয়েছে: {name}",
        "player_removed": "খেলোয়াড় সরানো হয়েছে: {name}",
        "player_already_tracked": "খেলোয়াড় ইতিমধ্যেই ট্র্যাক করা হয়েছে: {name}",
        "player_not_found": "খেলোয়াড় পাওয়া যায়নি: {name}",
        "language_set": "ভাষা {language} এ সেট করা হয়েছে",
        "invalid_language": "অবৈধ ভাষা কোড। বৈধ বিকল্প: {languages}",
        "current_language": "বর্তমান ভাষা: {language}",
        
        # Error messages
        "pubg_api_error": "PUBG API ত্রুটি: {error}",
        "something_went_wrong": "কিছু ভুল হয়েছে: {error}",
        "guild_only": "এই কমান্ডটি শুধুমাত্র Discord সার্ভারের ভিতরে কাজ করে — সেখানে চেষ্টা করুন।",
    },
    
    "pt": {
        # Common UI strings
        "not_configured": "Não configurado",
        "enabled": "Ativado",
        "disabled": "Desativado",
        "next_run": "Próxima execução",
        "due_now": "Vence agora (o agendador verifica a cada 15 minutos)",
        "scheduler_note": "O agendador verifica a cada 15 minutos; um relatório pode ser publicado logo após seu horário exibido.",
        
        # Report titles
        "clan_digest": "Resumo do clã",
        "last_active": "Última atividade",
        "ranked": "Classificado",
        "daily_highlights": "Destaques diários",
        "clan_level": "Nível do clã",
        "survival_mastery": "Maestria de sobrevivência",
        "donation_message": "Mensagem de doação",
        
        # Time expressions
        "every_hours": "A cada {hours} hora(s)",
        "daily_at": "Diariamente às {hour:02d}:{minute:02d} horário do leste",
        "every_weekday_at": "Toda {weekday} às {hour:02d}:{minute:02d} horário do leste",
        "every_sunday_at": "Todo domingo às {hour:02d}:{minute:02d} horário do leste",
        
        # Weekday names
        "monday": "Segunda-feira",
        "tuesday": "Terça-feira",
        "wednesday": "Quarta-feira",
        "thursday": "Quinta-feira",
        "friday": "Sexta-feira",
        "saturday": "Sábado",
        "sunday": "Domingo",
        
        # Embed descriptions
        "last_active_description": "A API da PUBG não expõe o histórico de login, então isso mostra a hora da **partida** mais recente de cada jogador, que é o sinal mais próximo disponível para \"última jogada\".",
        "scheduled_report_status": "Apenas relatórios configurados são agendados. Todos os horários são em UTC.",
        "no_reports_configured": "Ainda não há relatórios automáticos configurados. Use os comandos `/set...channel` e `/set...time` para agendar um.",
        
        # Status messages
        "active_24h": "Ativo nas últimas 24h",
        "tracked_players": "Jogadores rastreados",
        "protected_players": "Jogadores protegidos",
        "not_found": "Não encontrado",
        "protected_footer": "🛡️ = Protegido de remoção por inatividade",
        "updates_daily": "Atualizações diárias às 02:00 UTC (atualização ao vivo, não republicado)",
        
        # Last Active Report
        "last_active_report": "Relatório de última atividade",
        "last_active_description": "A API da PUBG não expõe o histórico de login, então isso mostra a hora da **partida** mais recente de cada jogador, que é o sinal mais próximo disponível para \"última jogada\".",
        "players": "Jogadores",
        "source_manual": " *(manual)*",
        "source_auto_count": " *(contagem automática)*",
        "less_than_1_hour": "Menos de 1 hora atrás",
        "hours_ago": "{hours} hora(s) atrás",
        "days_ago": "{days} dia(s) atrás",
        "no_recent_matches": "Nenhuma partida recente encontrada",
        
        # Clan Report
        "clan_report": "Relatório do clã",
        "tracked_players": "Jogadores rastreados",
        "total_kills": "Total de abates",
        "total_wins": "Total de vitórias",
        "win_rate": "Taxa de vitória",
        "total_damage": "Dano total",
        "total_matches": "Total de partidas",
        "top_fraggers": "Melhores abatedores",
        "lifetime_stats_footer": "Estatísticas da API oficial do PUBG · vitalício, por modo de jogo",
        
        # Clan Level Report
        "clan_level_report": "Nível do clã e progresso semanal",
        "current_level": "Nível atual",
        "members": "Membros",
        "weekly_progress": "Progresso semanal",
        "first_snapshot": "Este é o primeiro instantâneo do clã. O próximo relatório semanal mostrará a mudança de nível.",
        "level_change": "Mudança de nível desde o último relatório semanal: **{change:+d}**",
        "member_change": " · Mudança de membros: **{change:+d}**",
        "important_note": "Importante",
        "clan_level_note": "A API do PUBG expõe o nível do clã e o número de membros, mas não o XP necessário para o próximo nível. Portanto, o progresso é medido pela mudança no nível do clã entre relatórios semanais.",
        "weekly_clan_progress_footer": "Progresso semanal do clã · API oficial do PUBG",
        
        # Ranked Report
        "ranked_report": "Classificada",
        "ranked_description": "Classificações competitivas da temporada atual.",
        "highest_ranked": "Classificação mais alta",
        "ranked_this_season": "Classificados esta temporada",
        "ranking": "Classificação",
        "no_ranked_matches": "Sem partidas classificadas",
        "no_ranked_description": "Nenhum jogador rastreado tem partidas classificadas nesta fila esta temporada.",
        "ranked_footer": "Atualizações diárias às 04:30 UTC (atualização ao vivo, não republicado) · Estatísticas da API oficial do PUBG · classificada, temporada atual",
        
        # Daily Highlights Report
        "daily_highlights": "Destaques diários",
        "fun_titles": "Títulos divertidos",
        "highlights_description": "Com base em {count} jogador(es) que jogaram desde a redefinição diária (02:00 UTC).",
        "no_recent_matches_available": "Nenhuma partida recente disponível",
        "no_recent_matches_description": "A telemetria de partidas do PUBG está disponível apenas nos últimos 14 dias. {count} jogador(es) têm partidas mais antigas que não podem ser analisadas.",
        "no_matches_played": "Nenhuma partida jogada",
        "no_matches_description": "Ninguém na lista jogou nesta janela.",
        "top_10": "Top 10",
        "kills_best_match": "abates (melhor partida)",
        "dmg_best_match": "dano (melhor partida)",
        "human_bot_split": "humano / {count} bot",
        "matches_count": "partida(s)",
        "highlights_footer": "Atualizações diárias às 02:00 UTC (atualização ao vivo, não republicado) · Estatísticas da API oficial do PUBG · destaques diários, últimas 24 horas",
        
        # Chicken Dinner Report
        "chicken_dinner": "Frango assado",
        "recent_squad_wins": "Vitórias recentes de esquadrão (últimas 5 partidas por jogador)",
        "no_wins_yet": "Ainda não há vitórias de esquadrão hoje!",
        "total_wins_today": "Vitórias totais hoje",
        "chicken_dinner_footer": "Atualizações a cada 15 minutos · Redefinição diária às 02:00 UTC · Estatísticas da API oficial do PUBG",
        
        # Mastery Report
        "mastery_report": "Maestria de armas e sobrevivência",
        "mastery_description": "A maestria de arma de maior nível e a maestria de sobrevivência geral de cada jogador.",
        "top_weapon_mastery": "Melhor maestria de arma",
        "top_survival_level": "Melhor nível de sobrevivência",
        "mastery": "Maestria",
        "kills": "abates",
        "survival": "Sobrevivência",
        
        # Survival Mastery Report
        "survival_mastery_report": "Maestria de sobrevivência por nível",
        "survival_mastery_description": "Nível de maestria de sobrevivência de cada jogador, agrupado por nível.",
        "no_survival_data": "Nenhum dado de maestria de sobrevivência disponível.",
        
        # Leaderboard Report
        "leaderboard_report": "Resultados do ranking",
        "leaderboard_description": "Resultados de classificação oficial PUBG para jogadores rastreados.",
        "no_leaderboard_results": "Nenhum jogador rastreado encontrado no ranking.",
        
        # Report Status
        "report_status": "Status do relatório agendado",
        "report_status_description": "Apenas relatórios configurados são agendados. Todos os horários são UTC.",
        "no_reports_configured": "Ainda não há relatórios automáticos configurados. Use os comandos `/set...channel` e `/set...time` para agendar um.",
        "channel": "Canal",
        "schedule": "Cronograma",
        "next_run": "Próxima execução",
        "status": "Status",
        "enabled_status": "Habilitado",
        "disabled_status": "Desabilitado",
        
        # Command responses
        "no_players_tracked": "Ainda não há jogadores rastreados. Adicione alguns com `/addplayer`.",
        "player_added": "Jogador adicionado: {name}",
        "player_removed": "Jogador removido: {name}",
        "player_already_tracked": "Jogador já rastreado: {name}",
        "player_not_found": "Jogador não encontrado: {name}",
        "language_set": "Idioma definido para {language}",
        "invalid_language": "Código de idioma inválido. Opções válidas: {languages}",
        "current_language": "Idioma atual: {language}",
        
        # Error messages
        "pubg_api_error": "Erro da API PUBG: {error}",
        "something_went_wrong": "Algo deu errado: {error}",
        "guild_only": "Este comando só funciona dentro de um servidor Discord — tente lá.",
    },
    
    "id": {
        # Common UI strings
        "not_configured": "Tidak dikonfigurasi",
        "enabled": "Diaktifkan",
        "disabled": "Dinonaktifkan",
        "next_run": "Jalanan berikutnya",
        "due_now": "Jatuh tempo sekarang (penjadwal memeriksa setiap 15 menit)",
        "scheduler_note": "Penjadwal memeriksa setiap 15 menit; laporan dapat diposting tak lama setelah waktu yang ditampilkan.",
        
        # Report titles
        "clan_digest": "Ringkasan klan",
        "last_active": "Aktivitas terakhir",
        "ranked": "Peringkat",
        "daily_highlights": "Poin harian",
        "clan_level": "Level klan",
        "survival_mastery": "Penguasaan bertahan hidup",
        "donation_message": "Pesan donasi",
        
        # Time expressions
        "every_hours": "Setiap {hours} jam",
        "daily_at": "Harian di {hour:02d}:{minute:02d} waktu Timur",
        "every_weekday_at": "Setiap {weekday} di {hour:02d}:{minute:02d} waktu Timur",
        "every_sunday_at": "Setiap Minggu di {hour:02d}:{minute:02d} waktu Timur",
        
        # Weekday names
        "monday": "Senin",
        "tuesday": "Selasa",
        "wednesday": "Rabu",
        "thursday": "Kamis",
        "friday": "Jumat",
        "saturday": "Sabtu",
        "sunday": "Minggu",
        
        # Embed descriptions
        "last_active_description": "API PUBG tidak mengekspos riwayat login, jadi ini menunjukkan waktu **pertandingan** terbaru setiap pemain, yang merupakan sinyal terdekat yang tersedia untuk \"terakhir dimainkan\".",
        "scheduled_report_status": "Hanya laporan yang dikonfigurasi yang dijadwalkan. Semua waktu dalam UTC.",
        "no_reports_configured": "Belum ada laporan otomatis yang dikonfigurasi. Gunakan perintah `/set...channel` dan `/set...time` untuk menjadwalkan satu.",
        
        # Status messages
        "active_24h": "Aktif dalam 24 jam terakhir",
        "tracked_players": "Pemain dilacak",
        "protected_players": "Pemain dilindungi",
        "not_found": "Tidak ditemukan",
        "protected_footer": "🛡️ = Dilindungi dari penghapusan karena tidak aktif",
        "updates_daily": "Pembaruan harian pukul 02:00 UTC (pembaruan langsung, tidak diposting ulang)",
        
        # Last Active Report
        "last_active_report": "Laporan aktivitas terakhir",
        "last_active_description": "API PUBG tidak mengekspos riwayat login, jadi ini menunjukkan waktu **pertandingan** terbaru setiap pemain, yang merupakan sinyal terdekat yang tersedia untuk \"terakhir dimainkan\".",
        "players": "Pemain",
        "source_manual": " *(manual)*",
        "source_auto_count": " *(hitungan otomatis)*",
        "less_than_1_hour": "Kurang dari 1 jam yang lalu",
        "hours_ago": "{hours} jam yang lalu",
        "days_ago": "{days} hari yang lalu",
        "no_recent_matches": "Tidak ada pertandingan terbaru ditemukan",
        
        # Clan Report
        "clan_report": "Laporan klan",
        "tracked_players": "Pemain dilacak",
        "total_kills": "Total kill",
        "total_wins": "Total kemenangan",
        "win_rate": "Tingkat kemenangan",
        "total_damage": "Total kerusakan",
        "total_matches": "Total pertandingan",
        "top_fraggers": "Pembunuh terbaik",
        "lifetime_stats_footer": "Statistik dari API PUBG resmi · seumur hidup, per mode permainan",
        
        # Clan Level Report
        "clan_level_report": "Level klan dan kemajuan mingguan",
        "current_level": "Level saat ini",
        "members": "Anggota",
        "weekly_progress": "Kemajuan mingguan",
        "first_snapshot": "Ini adalah snapshot klan pertama. Laporan mingguan berikutnya akan menunjukkan perubahan level.",
        "level_change": "Perubahan level sejak laporan mingguan terakhir: **{change:+d}**",
        "member_change": " · Perubahan anggota: **{change:+d}**",
        "important_note": "Penting",
        "clan_level_note": "API PUBG mengekspos level klan dan jumlah anggota, tetapi tidak XP yang dibutuhkan untuk level berikutnya. Oleh karena itu, kemajuan diukur dengan perubahan level klan antara laporan mingguan.",
        "weekly_clan_progress_footer": "Kemajuan klan mingguan · API PUBG resmi",
        
        # Ranked Report
        "ranked_report": "Peringkat",
        "ranked_description": "Peringkat kompetitif musim saat ini.",
        "highest_ranked": "Peringkat tertinggi",
        "ranked_this_season": "Diperingkat musim ini",
        "ranking": "Peringkat",
        "no_ranked_matches": "Tidak ada pertandingan peringkat",
        "no_ranked_description": "Tidak ada pemain yang dilacak memiliki pertandingan peringkat di antrian ini musim ini.",
        "ranked_footer": "Pembaruan harian pukul 04:30 UTC (pembaruan langsung, tidak diposting ulang) · Statistik dari API PUBG resmi · peringkat, musim saat ini",
        
        # Daily Highlights Report
        "daily_highlights": "Poin harian",
        "fun_titles": "Judul lucu",
        "highlights_description": "Berdasarkan {count} pemain yang bermain sejak reset harian (02:00 UTC).",
        "no_recent_matches_available": "Tidak ada pertandingan terbaru tersedia",
        "no_recent_matches_description": "Telemetri pertandingan PUBG hanya tersedia selama 14 hari terakhir. {count} pemain memiliki pertandingan yang lebih lama yang tidak dapat dianalisis.",
        "no_matches_played": "Tidak ada pertandingan yang dimainkan",
        "no_matches_description": "Tidak ada orang di daftar yang bermain di jendela ini.",
        "top_10": "Top 10",
        "kills_best_match": "kill (pertandingan terbaik)",
        "dmg_best_match": "kerusakan (pertandingan terbaik)",
        "human_bot_split": "manusia / {count} bot",
        "matches_count": "pertandingan",
        "highlights_footer": "Pembaruan harian pukul 02:00 UTC (pembaruan langsung, tidak diposting ulang) · Statistik dari API PUBG resmi · poin harian, 24 jam terakhir",
        
        # Chicken Dinner Report
        "chicken_dinner": "Ayam panggang",
        "recent_squad_wins": "Kemenangan tim terbaru (5 pertandingan terakhir per pemain)",
        "no_wins_yet": "Belum ada kemenangan tim hari ini!",
        "total_wins_today": "Total kemenangan hari ini",
        "chicken_dinner_footer": "Pembaruan setiap 15 menit · Reset harian pukul 02:00 UTC · Statistik dari API PUBG resmi",
        
        # Mastery Report
        "mastery_report": "Penguasaan senjata dan bertahan hidup",
        "mastery_description": "Penguasaan senjata tingkat tertinggi dan penguasaan bertahan hidup keseluruhan setiap pemain.",
        "top_weapon_mastery": "Penguasaan senjata terbaik",
        "top_survival_level": "Level bertahan hidup terbaik",
        "mastery": "Penguasaan",
        "kills": "bunuh",
        "survival": "Bertahan hidup",
        
        # Survival Mastery Report
        "survival_mastery_report": "Penguasaan bertahan hidup berdasarkan level",
        "survival_mastery_description": "Level penguasaan bertahan hidup setiap pemain, dikelompokkan berdasarkan level.",
        "no_survival_data": "Tidak ada data penguasaan bertahan hidup yang tersedia.",
        
        # Leaderboard Report
        "leaderboard_report": "Hasil papan peringkat",
        "leaderboard_description": "Hasil penempatan papan peringkat PUBG resmi untuk pemain yang dilacak.",
        "no_leaderboard_results": "Tidak ada pemain yang dilacak ditemukan di papan peringkat.",
        
        # Report Status
        "report_status": "Status laporan terjadwal",
        "report_status_description": "Hanya laporan yang dikonfigurasi yang dijadwalkan. Semua waktu adalah UTC.",
        "no_reports_configured": "Belum ada laporan otomatis yang dikonfigurasi. Gunakan perintah `/set...channel` dan `/set...time` untuk menjadwalkan satu.",
        "channel": "Saluran",
        "schedule": "Jadwal",
        "next_run": "Jalankan berikutnya",
        "status": "Status",
        "enabled_status": "Diaktifkan",
        "disabled_status": "Dinonaktifkan",
        
        # Command responses
        "no_players_tracked": "Belum ada pemain yang dilacak. Tambahkan beberapa dengan `/addplayer`.",
        "player_added": "Pemain ditambahkan: {name}",
        "player_removed": "Pemain dihapus: {name}",
        "player_already_tracked": "Pemain sudah dilacak: {name}",
        "player_not_found": "Pemain tidak ditemukan: {name}",
        "language_set": "Bahasa diatur ke {language}",
        "invalid_language": "Kode bahasa tidak valid. Opsi valid: {languages}",
        "current_language": "Bahasa saat ini: {language}",
        
        # Error messages
        "pubg_api_error": "Kesalahan API PUBG: {error}",
        "something_went_wrong": "Terjadi kesalahan: {error}",
        "guild_only": "Perintah ini hanya berfungsi di dalam server Discord — coba di sana.",
    },
    
    "ur": {
        # Common UI strings
        "not_configured": "کنفیگر نہیں",
        "enabled": "فعال",
        "disabled": "غیر فعال",
        "next_run": "اگلا رن",
        "due_now": "ابھی نہیں (شیڈولر ہر 15 منٹ میں چیک کرتا ہے)",
        "scheduler_note": "شیڈولر ہر 15 منٹ میں چیک کرتا ہے؛ رپورٹ اپنے ظاہر کردہ وقت کے بعد جلدی پوسٹ ہو سکتی ہے۔",
        
        # Report titles
        "clan_digest": "کلان ڈائجسٹ",
        "last_active": "آخری فعال",
        "ranked": "رینکڈ",
        "daily_highlights": "روزانہ ہائی لائٹس",
        "clan_level": "کلان لیول",
        "survival_mastery": "بقا کی مہارت",
        "donation_message": "عطیہ کا پیغام",
        
        # Time expressions
        "every_hours": "ہر {hours} گھنٹے",
        "daily_at": "روزانہ {hour:02d}:{minute:02d} UTC",
        "every_weekday_at": "ہر {weekday} {hour:02d}:{minute:02d} UTC",
        "every_sunday_at": "ہر اتوار {hour:02d}:{minute:02d} UTC",
        
        # Weekday names
        "monday": "پیر",
        "tuesday": "منگل",
        "wednesday": "بدھ",
        "thursday": "جمعرات",
        "friday": "جمعہ",
        "saturday": "ہفتہ",
        "sunday": "اتوار",
        
        # Embed descriptions
        "last_active_description": "PUBG API لاگ ان ہسٹری کو ظاہر نہیں کرتا، اس لیے یہ ہر کھلاڑی کے حالیہ **میچ** کا وقت دکھاتا ہے، جو \"آخری کھیلا\" کے لیے دستیاب قریب ترین سگنل ہے۔",
        "scheduled_report_status": "صرف کنفیگر کردہ رپورٹس شیڈول ہوتی ہیں۔ تمام اوقات UTC میں ہیں۔",
        "no_reports_configured": "ابھی تک کوئی خودکار رپورٹ کنفیگر نہیں کی گئی۔ ایک شیڈول کرنے کے لیے `/set...channel` اور `/set...time` کمانڈز استعمال کریں۔",
        
        # Status messages
        "active_24h": "پچھلے 24 گھنٹوں میں فعال",
        "tracked_players": "ٹریک کیے گئے کھلاڑی",
        "protected_players": "محفوظ کھلاڑی",
        "not_found": "نہیں ملا",
        "protected_footer": "🛡️ = عدم فعالیت سے ہٹانے سے محفوظ",
        "updates_daily": "روزانہ UTC رات 2 بجے اپ ڈیٹ (لائیو اپ ڈیٹ، دوبارہ پوسٹ نہیں)",
        
        # Last Active Report
        "last_active_report": "آخری فعال رپورٹ",
        "last_active_description": "PUBG API لاگ ان ہسٹری کو ظاہر نہیں کرتا، اس لیے یہ ہر کھلاڑی کے حالیہ **میچ** کا وقت دکھاتا ہے، جو \"آخری کھیلا\" کے لیے دستیاب قریب ترین سگنل ہے۔",
        "players": "کھلاڑی",
        "source_manual": " *(دستی)*",
        "source_auto_count": " *(خودکار گنتی)*",
        "less_than_1_hour": "1 گھنٹے سے کم پہلے",
        "hours_ago": "{hours} گھنٹے پہلے",
        "days_ago": "{days} دن پہلے",
        "no_recent_matches": "حالیہ میچ نہیں ملا",
        
        # Clan Report
        "clan_report": "کلان رپورٹ",
        "tracked_players": "ٹریک کیے گئے کھلاڑی",
        "total_kills": "کل کلز",
        "total_wins": "کل جیت",
        "win_rate": "جیت کی شرح",
        "total_damage": "کل نقصان",
        "total_matches": "کل میچز",
        "top_fraggers": "بہترین فرگرز",
        "lifetime_stats_footer": "آفیشیل PUBG API سے اعدادوشمار · آجیونک، فی گیم موڈ",
        
        # Clan Level Report
        "clan_level_report": "کلان لیول اور ہفتہ وار پیشرفت",
        "current_level": "موجودہ لیول",
        "members": "ممبرز",
        "weekly_progress": "ہفتہ وار پیشرفت",
        "first_snapshot": "یہ پہلا کلان سنیپ شاٹ ہے۔ اگلا ہفتہ وار رپورٹ لیول تبدیلی دکھائے گا۔",
        "level_change": "آخری ہفتہ وار رپورٹ سے لیول تبدیلی: **{change:+d}**",
        "member_change": " · ممبر تبدیلی: **{change:+d}**",
        "important_note": "اہم",
        "clan_level_note": "PUBG کلان لیول اور ممبرز کی تعداد ظاہر کرتا ہے، لیکن اگلے لیول کے لیے درکار XP نہیں۔ لہذا، پیشرفت ہفتہ وار رپورٹ کے درمیان کلان لیول تبدیلی سے ماپی جاتی ہے۔",
        "weekly_clan_progress_footer": "ہفتہ وار کلان پیشرفت · آفیشیل PUBG API",
        
        # Ranked Report
        "ranked_report": "رینکڈ",
        "ranked_description": "موجودہ سیزن کی مقابلہاری رینکڈ اسٹینڈنگز۔",
        "highest_ranked": "سب سے زیادہ رینکڈ",
        "ranked_this_season": "اس سیزن میں رینکڈ",
        "ranking": "رینکنگ",
        "no_ranked_matches": "کوئی رینکڈ میچ نہیں",
        "no_ranked_description": "اس سیزن میں اس قطار میں کوئی ٹریک کیا گیا کھلاڑی کے پاس رینکڈ میچ نہیں ہیں۔",
        "ranked_footer": "روزانہ UTC رات 4:30 بجے اپ ڈیٹ (لائیو اپ ڈیٹ، دوبارہ پوسٹ نہیں) · آفیشیل PUBG API سے اعدادوشمار · رینکڈ، موجودہ سیزن",
        
        # Daily Highlights Report
        "daily_highlights": "روزانہ ہائی لائٹس",
        "fun_titles": "مذاق کے عناوین",
        "highlights_description": "روزانہ ری سیٹ (UTC رات 2 بجے) کے بعد کھیلنے والے {count} کھلاڑیوں کے مبنی۔",
        "no_recent_matches_available": "کوئی حالیہ میچ دستیاب نہیں",
        "no_recent_matches_description": "PUBG میچ ٹیلی میٹری صرف پچھلے 14 دنوں کے لیے دستیاب ہے۔ {count} کھلاڑیوں کے پرانے میچ ہیں جن کا تجزیہ نہیں کیا جا سکتا۔",
        "no_matches_played": "کوئی میچ نہیں کھیلا",
        "no_matches_description": "اسٹر پر اس ونڈو میں کسی نے نہیں کھیلا۔",
        "top_10": "پہلے 10",
        "kills_best_match": "کلز (بہترین میچ)",
        "dmg_best_match": "نقصان (بہترین میچ)",
        "human_bot_split": "انسان / {count} بوٹ",
        "matches_count": "میچ",
        "highlights_footer": "روزانہ UTC رات 2 بجے اپ ڈیٹ (لائیو اپ ڈیٹ، دوبارہ پوسٹ نہیں) · آفیشیل PUBG API سے اعدادوشمار · روزانہ ہائی لائٹس، گوزرے 24 گھنٹے",
        
        # Chicken Dinner Report
        "chicken_dinner": "چکن ڈنر",
        "recent_squad_wins": "حالیہ اسکواڈ جیت (فی کھلاڑی پچھلے 5 میچ)",
        "no_wins_yet": "آج تک کوئی اسکواڈ جیت نہیں!",
        "total_wins_today": "آج کل جیت",
        "chicken_dinner_footer": "ہر 15 منٹ میں اپ ڈیٹ · روزانہ UTC رات 4 بجے ری سیٹ · آفیشیل PUBG API سے اعدادوشمار",
        
        # Mastery Report
        "mastery_report": "ہتھیار اور بقا کی مہارت",
        "mastery_description": "ہر کھلاڑی کا سب سے از درجے ہتھیار اور مجموعی بقا کی مہارت۔",
        "top_weapon_mastery": "سب سے درجے ہتھیار",
        "top_survival_level": "سب سے درجے بقا کی سطح",
        "mastery": "مہارت",
        "kills": "کلز",
        "survival": "بقا",
        
        # Survival Mastery Report
        "survival_mastery_report": "سطح کے مطابق بقا کی مہارت",
        "survival_mastery_description": "ہر کھلاڑی کی بقا کی مہارت سطح، سطح کے مطابق گروپ کی گئی۔",
        "no_survival_data": "کوئی بقا کی مہارت ڈیٹا دستیاب نہیں۔",
        
        # Leaderboard Report
        "leaderboard_report": "لیڈر بورڈ نتائج",
        "leaderboard_description": "ٹریک کیے گئے کھلاڑیوں کے لیے آفیشیل PUBG لیڈر بورڈ پلیسمنٹ نتائج۔",
        "no_leaderboard_results": "لیڈر بورڈ پر کوئی ٹریک کیا گیا کھلاڑی نہیں ملا۔",
        
        # Report Status
        "report_status": "شیڈول شدہ رپورٹ کی حیثیت",
        "report_status_description": "صرف کنفیگر شدہ رپورٹ شیڈول کیے جاتے ہیں۔ تمام اوقات UTC ہیں۔",
        "no_reports_configured": "ابھی تک کوئی خودکار رپورٹ کنفیگر نہیں کی گئی۔ ایک شیڈول کرنے کے لیے `/set...channel` اور `/set...time` کمانڈز استعمال کریں۔",
        "channel": "چینل",
        "schedule": "شیڈول",
        "next_run": "اگلا رن",
        "status": "حیثیت",
        "enabled_status": "فعال",
        "disabled_status": "غیر فعال",
        
        # Command responses
        "no_players_tracked": "ابھی تک کوئی کھلاڑی ٹریک نہیں کیا گیا۔ `/addplayer` کے ساتھ کچھ شامل کریں۔",
        "player_added": "کھلاڑی شامل کیا گیا: {name}",
        "player_removed": "کھلاڑی ہٹا دیا گیا: {name}",
        "player_already_tracked": "کھلاڑی پہلے سے ٹریک کیا گیا: {name}",
        "player_not_found": "کھلاڑی نہیں ملا: {name}",
        "language_set": "زبان {language} پر سیٹ کی گئی",
        "invalid_language": "غلط زبان کوڈ۔ درست اختیارات: {languages}",
        "current_language": "موجودہ زبان: {language}",
        
        # Error messages
        "pubg_api_error": "PUBG API خرابی: {error}",
        "something_went_wrong": "کچھ غلط ہو گیا: {error}",
        "guild_only": "یہ کمانڈ صرف Discord سرور کے اندر کام کرتی ہے — وہاں کوشش کریں۔",
    },
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
