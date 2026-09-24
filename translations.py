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
        "updates_daily": "Updates daily at 10:00pm EST (live-updating, not reposted)",
        
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
        "updates_daily": "每天EST晚上10点更新（实时更新，不重新发布）",
        
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
        "updates_daily": "Actualizaciones diarias a las 10:00pm EST (actualización en vivo, no republicado)",
        
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
        "scheduled_report_status": "केवल कॉन्फ़िगर किए गए रिपोर्ट शेड्यूल किए जाते हैं। सभी समय पूर्वी हैं और स्वचालित रूप से EST/EDT का पालन करते हैं।",
        "no_reports_configured": "अभी तक कोई स्वचालित रिपोर्ट कॉन्फ़िगर नहीं की गई है। एक को शेड्यूल करने के लिए `/set...channel` और `/set...time` कमांड का उपयोग करें।",
        
        # Status messages
        "active_24h": "पिछले 24 घंटे में सक्रिय",
        "tracked_players": "ट्रैक किए गए खिलाड़ी",
        "protected_players": "संरक्षित खिलाड़ी",
        "not_found": "नहीं मिला",
        "protected_footer": "🛡️ = निष्क्रियता हटाने से संरक्षित",
        "updates_daily": "दैनिक EST रात 10 बजे अपडेट (लाइव अपडेट, पुनः पोस्ट नहीं)",
        
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
        "scheduled_report_status": "يتم جدولة التقارير المهيأة فقط. جميع الأوقات شرقية وتتبع تلقائيًا EST/EDT.",
        "no_reports_configured": "لم يتم تكوين أي تقارير تلقائية بعد. استخدم أوامر `/set...channel` و `/set...time` لجدولة واحدة.",
        
        # Status messages
        "active_24h": "نشط في آخر 24 ساعة",
        "tracked_players": "اللاعبون المتتبعون",
        "protected_players": "اللاعبون المحميون",
        "not_found": "غير موجود",
        "protected_footer": "🛡️ = محمي من الإزالة بسبب عدم النشاط",
        "updates_daily": "تحديثات يومية الساعة 10:00 مساءً EST (تحديث مباشر، لا إعادة نشر)",
        
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
        "daily_at": "Quotidien à {hour:02d}:{minute:02d} heure de l'Est",
        "every_weekday_at": "Chaque {weekday} à {hour:02d}:{minute:02d} heure de l'Est",
        "every_sunday_at": "Chaque dimanche à {hour:02d}:{minute:02d} heure de l'Est",
        
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
        "scheduled_report_status": "Seuls les rapports configurés sont planifiés. Toutes les heures sont de l'Est et suivent automatiquement EST/EDT.",
        "no_reports_configured": "Aucun rapport automatique n'est encore configuré. Utilisez les commandes `/set...channel` et `/set...time` pour en planifier un.",
        
        # Status messages
        "active_24h": "Actif au cours des 24 dernières heures",
        "tracked_players": "Joueurs suivis",
        "protected_players": "Joueurs protégés",
        "not_found": "Non trouvé",
        "protected_footer": "🛡️ = Protégé de la suppression par inactivité",
        "updates_daily": "Mises à jour quotidiennes à 22h00 EST (mise à jour en direct, non republié)",
        
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
        "daily_at": "দৈনিক {hour:02d}:{minute:02d} পূর্বাঞ্চল সময়",
        "every_weekday_at": "প্রতি {weekday} {hour:02d}:{minute:02d} পূর্বাঞ্চল সময়",
        "every_sunday_at": "প্রতি রবিবার {hour:02d}:{minute:02d} পূর্বাঞ্চল সময়",
        
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
        "scheduled_report_status": "শুধুমাত্র কনফিগার করা রিপোর্টগুলি নির্ধারিত হয়। সমস্ত সময় পূর্বাঞ্চল এবং স্বয়ংক্রিয়ভাবে EST/EDT অনুসরণ করে।",
        "no_reports_configured": "এখনও কোনো স্বয়ংক্রিয় রিপোর্ট কনফিগার করা হয়নি। একটি নির্ধারণ করতে `/set...channel` এবং `/set...time` কমান্ড ব্যবহার করুন।",
        
        # Status messages
        "active_24h": "গত 24 ঘন্টায় সক্রিয়",
        "tracked_players": "ট্র্যাক করা খেলোয়াড়",
        "protected_players": "সুরক্ষিত খেলোয়াড়",
        "not_found": "পাওয়া যায়নি",
        "protected_footer": "🛡️ = নিষ্ক্রিয়তা অপসারণ থেকে সুরক্ষিত",
        "updates_daily": "দৈনিক EST রাত 10 টায় আপডেট (লাইভ আপডেট, পুনঃপোস্ট নয়)",
        
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
        "scheduled_report_status": "Apenas relatórios configurados são agendados. Todos os horários são do leste e seguem automaticamente EST/EDT.",
        "no_reports_configured": "Ainda não há relatórios automáticos configurados. Use os comandos `/set...channel` e `/set...time` para agendar um.",
        
        # Status messages
        "active_24h": "Ativo nas últimas 24h",
        "tracked_players": "Jogadores rastreados",
        "protected_players": "Jogadores protegidos",
        "not_found": "Não encontrado",
        "protected_footer": "🛡️ = Protegido de remoção por inatividade",
        "updates_daily": "Atualizações diárias às 22:00 EST (atualização ao vivo, não republicado)",
        
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
        "scheduled_report_status": "Hanya laporan yang dikonfigurasi yang dijadwalkan. Semua waktu adalah Timur dan secara otomatis mengikuti EST/EDT.",
        "no_reports_configured": "Belum ada laporan otomatis yang dikonfigurasi. Gunakan perintah `/set...channel` dan `/set...time` untuk menjadwalkan satu.",
        
        # Status messages
        "active_24h": "Aktif dalam 24 jam terakhir",
        "tracked_players": "Pemain dilacak",
        "protected_players": "Pemain dilindungi",
        "not_found": "Tidak ditemukan",
        "protected_footer": "🛡️ = Dilindungi dari penghapusan karena tidak aktif",
        "updates_daily": "Pembaruan harian pukul 22:00 EST (pembaruan langsung, tidak diposting ulang)",
        
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
        "daily_at": "روزانہ {hour:02d}:{minute:02d} مشرقی وقت",
        "every_weekday_at": "ہر {weekday} {hour:02d}:{minute:02d} مشرقی وقت",
        "every_sunday_at": "ہر اتوار {hour:02d}:{minute:02d} مشرقی وقت",
        
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
        "scheduled_report_status": "صرف کنفیگر کردہ رپورٹس شیڈول ہوتی ہیں۔ تمام اوقات مشرقی ہیں اور خود بخود EST/EDT کی پیروی کرتے ہیں۔",
        "no_reports_configured": "ابھی تک کوئی خودکار رپورٹ کنفیگر نہیں کی گئی۔ ایک شیڈول کرنے کے لیے `/set...channel` اور `/set...time` کمانڈز استعمال کریں۔",
        
        # Status messages
        "active_24h": "پچھلے 24 گھنٹوں میں فعال",
        "tracked_players": "ٹریک کیے گئے کھلاڑی",
        "protected_players": "محفوظ کھلاڑی",
        "not_found": "نہیں ملا",
        "protected_footer": "🛡️ = عدم فعالیت سے ہٹانے سے محفوظ",
        "updates_daily": "روزانہ EST رات 10 بجے اپ ڈیٹ (لائیو اپ ڈیٹ، دوبارہ پوسٹ نہیں)",
        
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
