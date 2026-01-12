/***************
 * CONFIG
 ***************/
const SHEET_BOOKINGS = "Bookings";
const SHEET_SETTINGS = "Settings";
const SHEET_SLOT_EVENTS = "SlotEvents";

// Вставь Calendar ID (из настроек календаря)
const BOSS_CALENDAR_ID = "8488c356a58074a09a4efa3605e61d859062f221086f37d5339c877a875a47f1@group.calendar.google.com";

// Простой ключ для API (потом положишь в .env бота)
const API_KEY = "CHANGE_ME_SUPER_SECRET";

// Тайм-слоты 10:00..22:00
function getTimeSlots() {
  const out = [];
  for (let h = 10; h <= 22; h++) out.push(String(h).padStart(2, "0") + ":00");
  return out;
}

// Маппинг услуг -> ключи вместимости
function serviceToCapKey(service) {
  if (service.includes("групповая")) return "cap_paddle_group";
  if (service.includes("индивидуальная")) return "cap_paddle_ind";
  if (service.includes("Фитнес") || service.includes("фитнес")) return "cap_fitness";
  return "cap_paddle_ind";
}

function requireAuth_(e) {
  const key = (e.parameter && e.parameter.key) ? e.parameter.key : null;

  // для POST будем читать из тела
  // но в doPost мы проверим отдельно
  if (key && key === API_KEY) return true;
  return false;
}

function json_(obj, code) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function getSheet_(name) {
  return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
}

function getSettingsMap_() {
  const sh = getSheet_(SHEET_SETTINGS);
  const values = sh.getDataRange().getValues(); // [ [key,value], ... ]
  const m = {};
  for (let i = 1; i < values.length; i++) {
    const k = String(values[i][0]).trim();
    const v = String(values[i][1]).trim();
    if (k) m[k] = v;
  }
  return m;
}

function setSetting_(key, value) {
  const sh = getSheet_(SHEET_SETTINGS);
  const values = sh.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (String(values[i][0]).trim() === key) {
      sh.getRange(i + 1, 2).setValue(String(value));
      return;
    }
  }
  // если нет — добавим
  sh.appendRow([key, String(value)]);
}

function nextId_() {
  const sh = getSheet_(SHEET_BOOKINGS);
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return 1;
  const lastId = sh.getRange(lastRow, 1).getValue();
  const n = parseInt(lastId, 10);
  return isNaN(n) ? (lastRow - 1) : (n + 1);
}

function normDate_(v) {
  if (v instanceof Date) {
    return Utilities.formatDate(v, Session.getScriptTimeZone(), "dd.MM.yyyy");
  }
  return String(v).trim();
}

function normTime_(v) {
  // time может быть Date (если в ячейке время) или number (доля дня)
  if (v instanceof Date) {
    return Utilities.formatDate(v, Session.getScriptTimeZone(), "HH:mm");
  }
  if (typeof v === "number") {
    // v = доля дня (например 0.458333 для 11:00)
    const ms = Math.round(v * 24 * 60 * 60 * 1000);
    const d = new Date(ms);
    return Utilities.formatDate(d, "GMT", "HH:mm");
  }
  return String(v).trim();
}

function listActiveBookings_(service, dateStr, timeStr) {
  const sh = getSheet_(SHEET_BOOKINGS);
  const values = sh.getDataRange().getValues();

  const out = [];
  for (let i = 1; i < values.length; i++) {
    const status = String(values[i][3]).trim().toLowerCase();
    const svc = String(values[i][4]).trim();
    const d = normDate_(values[i][5]);   // ✅
    const t = normTime_(values[i][6]);   // ✅

    if (status === "active" && svc === service && d === dateStr && t === timeStr) {
      out.push({
        id: values[i][0],
        name: values[i][7],
        phone: values[i][8],
        source: values[i][2],
      });
    }
  }
  return out;
}


function countActive_(service, dateStr, timeStr) {
  return listActiveBookings_(service, dateStr, timeStr).length;
}

/***************
 * CALENDAR SYNC
 ***************/
function slotKey_(service, dateStr, timeStr) {
  return service + "|" + dateStr + "|" + timeStr;
}

function getEventIdBySlot_(slotKey) {
  const sh = getSheet_(SHEET_SLOT_EVENTS);
  const values = sh.getDataRange().getValues(); // [slot_key,event_id]
  for (let i = 1; i < values.length; i++) {
    if (String(values[i][0]).trim() === slotKey) return String(values[i][1]).trim();
  }
  return null;
}

function setEventIdBySlot_(slotKey, eventId) {
  const sh = getSheet_(SHEET_SLOT_EVENTS);
  const values = sh.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (String(values[i][0]).trim() === slotKey) {
      sh.getRange(i + 1, 2).setValue(eventId);
      return;
    }
  }
  sh.appendRow([slotKey, eventId]);
}

// dateStr: DD.MM.YYYY, timeStr: HH:MM
function parseDateTime_(dateStr, timeStr) {
  const [dd, mm, yyyy] = dateStr.split(".");
  const [HH, MM] = timeStr.split(":");
  return new Date(
    parseInt(yyyy, 10),
    parseInt(mm, 10) - 1,
    parseInt(dd, 10),
    parseInt(HH, 10),
    parseInt(MM, 10),
    0
  );
}

function upsertCalendarEvent_(service, dateStr, timeStr) {
  const settings = getSettingsMap_();
  const capKey = serviceToCapKey(service);
  const cap = parseInt(settings[capKey] || "1", 10);

  const participants = listActiveBookings_(service, dateStr, timeStr);
  const used = participants.length;

  const slotKey = slotKey_(service, dateStr, timeStr);
  const existingEventId = getEventIdBySlot_(slotKey);

  const cal = CalendarApp.getCalendarById(BOSS_CALENDAR_ID);
  const start = parseDateTime_(dateStr, timeStr);
  const end = new Date(start.getTime() + 60 * 60 * 1000); // 1 час

  const title = `${service} ${used}/${cap}`;
  const descLines = [
    `Слот: ${dateStr} ${timeStr}`,
    `Вместимость: ${used}/${cap}`,
    "",
    "Участники:",
  ];
  if (participants.length === 0) {
    descLines.push("— пока нет");
  } else {
    for (const p of participants) {
      descLines.push(`• ${p.name} (${p.phone}) [${p.source}]`);
    }
  }
  const description = descLines.join("\n");

  // Если никого нет — можно удалить событие, чтобы календарь был чистым.
  // Но боссу иногда приятно видеть пустые слоты? Не надо.
  if (used === 0 && existingEventId) {
    try {
      const ev = cal.getEventById(existingEventId);
      if (ev) ev.deleteEvent();
    } catch (e) {}
    setEventIdBySlot_(slotKey, "");
    return;
  }

  if (existingEventId) {
    const ev = cal.getEventById(existingEventId);
    if (ev) {
      ev.setTitle(title);
      ev.setDescription(description);
      ev.setTime(start, end);
      return;
    }
  }

  // create new
  const evNew = cal.createEvent(title, start, end, { description });
  setEventIdBySlot_(slotKey, evNew.getId());
}

/***************
 * HTTP HANDLERS
 ***************/
function doGet(e) {
  if (!requireAuth_(e)) {
    return json_({ ok: false, error: "unauthorized" }, 401);
  }

  const action = (e.parameter.action || "").trim();

  if (action === "settings") {
    const s = getSettingsMap_();
    return json_({ ok: true, settings: s });
  }

  if (action === "availability") {
    const service = (e.parameter.service || "").trim();
    const dateStr = (e.parameter.date || "").trim();
    if (!service || !dateStr) return json_({ ok: false, error: "missing params" }, 400);

    const settings = getSettingsMap_();
    const cap = parseInt(settings[serviceToCapKey(service)] || "1", 10);

    const times = getTimeSlots();
    const available = [];
    for (const t of times) {
      const used = countActive_(service, dateStr, t);
      if (used < cap) available.push(t);
    }

    return json_({ ok: true, available_times: available, cap });
  }

  return json_({ ok: false, error: "unknown action" }, 400);
}

function doPost(e) {
  // auth: key в query ?key=..., и/или в JSON body field "key"
  let body = {};
  try {
    body = JSON.parse(e.postData.contents || "{}");
  } catch (err) {
    body = {};
  }

  const key = (e.parameter && e.parameter.key) ? e.parameter.key : (body.key || null);
  if (key !== API_KEY) {
    return json_({ ok: false, error: "unauthorized" }, 401);
  }

  const action = (body.action || "").trim();

  if (action === "booking.create") {
    const service = String(body.service || "").trim();
    const dateStr = String(body.date || "").trim();
    const timeStr = String(body.time || "").trim();
    const name = String(body.name || "").trim();
    const phone = String(body.phone || "").trim();
    const tgUserId = String(body.tg_user_id || "").trim();
    const source = String(body.source || "bot").trim(); // bot / phone

    if (!service || !dateStr || !timeStr || !name || !phone) {
      return json_({ ok: false, error: "missing fields" }, 400);
    }

    // check capacity
    const settings = getSettingsMap_();
    const cap = parseInt(settings[serviceToCapKey(service)] || "1", 10);
    const used = countActive_(service, dateStr, timeStr);
    if (used >= cap) {
      return json_({ ok: false, error: "slot_full" }, 409);
    }

    const sh = getSheet_(SHEET_BOOKINGS);
    const id = nextId_();
    const createdAt = new Date();

    sh.appendRow([
      id,
      createdAt,
      source,
      "active",
      service,
      dateStr,
      timeStr,
      name,
      phone,
      tgUserId,
      ""
    ]);

    // sync calendar
    upsertCalendarEvent_(service, dateStr, timeStr);

    return json_({ ok: true, id });
  }

  if (action === "booking.cancel") {
    const id = String(body.id || "").trim();
    if (!id) return json_({ ok: false, error: "missing id" }, 400);

    const sh = getSheet_(SHEET_BOOKINGS);
    const values = sh.getDataRange().getValues();

    // find row, mark cancelled
    for (let i = 1; i < values.length; i++) {
      if (String(values[i][0]).trim() === id) {
        // already cancelled?
        const status = String(values[i][3]).trim();
        if (status !== "active") return json_({ ok: true, already: true });

        sh.getRange(i + 1, 4).setValue("cancelled");

        const service = String(values[i][4]).trim();
        const dateStr = String(values[i][5]).trim();
        const timeStr = String(values[i][6]).trim();

        // sync calendar
        upsertCalendarEvent_(service, dateStr, timeStr);

        return json_({ ok: true });
      }
    }
    return json_({ ok: false, error: "not_found" }, 404);
  }

  if (action === "settings.set") {
    const updates = body.updates || {};
    for (const k in updates) {
      setSetting_(k, String(updates[k]));
    }
    return json_({ ok: true });
  }

  return json_({ ok: false, error: "unknown action" }, 400);
}
