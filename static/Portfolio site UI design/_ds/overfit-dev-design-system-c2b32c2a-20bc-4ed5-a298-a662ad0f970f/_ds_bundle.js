/* @ds-bundle: {"format":4,"namespace":"OverfitDevDesignSystem_c2b32c","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Link","sourcePath":"components/core/Link.jsx"},{"name":"Panel","sourcePath":"components/core/Panel.jsx"},{"name":"StatusDot","sourcePath":"components/core/StatusDot.jsx"},{"name":"DataTable","sourcePath":"components/data/DataTable.jsx"},{"name":"PageHeader","sourcePath":"components/data/PageHeader.jsx"},{"name":"SectionTitle","sourcePath":"components/data/SectionTitle.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"57d5a6737c64","components/core/Button.jsx":"ade18ac571be","components/core/Link.jsx":"cd829afb6116","components/core/Panel.jsx":"40c56fbaa640","components/core/StatusDot.jsx":"a9cf5819ce11","components/data/DataTable.jsx":"32a060558ea1","components/data/PageHeader.jsx":"f7f1485180de","components/data/SectionTitle.jsx":"9111571748f2","components/forms/Input.jsx":"509db4709eb5","ui_kits/homelab/HomelabDashboard.jsx":"aca8c78bc78a","ui_kits/homelab/ServiceSection.jsx":"90c33c8f5332","ui_kits/homelab/services.js":"2f024403fdfc"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.OverfitDevDesignSystem_c2b32c = window.OverfitDevDesignSystem_c2b32c || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TONES = {
  neutral: {
    color: "var(--text-muted)",
    border: "var(--border-subtle)"
  },
  accent: {
    color: "var(--accent)",
    border: "var(--green-800)"
  },
  warn: {
    color: "var(--status-warn)",
    border: "#5c4a1a"
  },
  error: {
    color: "var(--status-error)",
    border: "#5c1a1a"
  },
  info: {
    color: "var(--status-info)",
    border: "#1a465c"
  }
};

/** Hairline square label for ports, states and counts. */
function Badge({
  tone = "neutral",
  solid = false,
  children,
  style,
  ...rest
}) {
  const t = TONES[tone] || TONES.neutral;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: "inline-block",
      fontSize: "var(--fs-small)",
      lineHeight: 1.5,
      padding: "0 5px",
      borderRadius: "var(--radius-none)",
      border: solid ? "1px solid transparent" : "1px solid " + t.border,
      background: solid ? t.color : "transparent",
      color: solid ? "var(--bg-page)" : t.color,
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const SIZES = {
  sm: {
    padding: "2px 8px",
    fontSize: "var(--fs-small)"
  },
  md: {
    padding: "4px 12px",
    fontSize: "var(--fs-body)"
  }
};

/** Square, hairline-bordered button. Three variants: primary, secondary, ghost. */
function Button({
  variant = "secondary",
  size = "md",
  disabled = false,
  children,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const [down, setDown] = React.useState(false);
  const skins = {
    primary: {
      background: down ? "var(--accent-press)" : hover ? "var(--accent-hover)" : "var(--accent)",
      color: "var(--text-on-accent)",
      border: "1px solid transparent"
    },
    secondary: {
      background: down ? "var(--surface-active)" : hover ? "var(--surface-hover)" : "transparent",
      color: "var(--text-heading)",
      border: "1px solid var(--border-subtle)"
    },
    ghost: {
      background: down ? "var(--surface-active)" : hover ? "var(--surface-hover)" : "transparent",
      color: "var(--text-muted)",
      border: "1px solid transparent"
    }
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    disabled: disabled,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setDown(false);
    },
    onMouseDown: () => setDown(true),
    onMouseUp: () => setDown(false),
    style: {
      font: "inherit",
      fontFamily: "var(--font-mono)",
      lineHeight: "var(--lh-snug)",
      borderRadius: "var(--radius-none)",
      cursor: disabled ? "default" : "pointer",
      transition: "var(--transition-color)",
      opacity: disabled ? 0.35 : 1,
      pointerEvents: disabled ? "none" : "auto",
      ...SIZES[size],
      ...skins[variant],
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Link.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Inverted-highlight link. On hover the text and background swap. */
function Link({
  href,
  children,
  muted = false,
  external = false,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const base = {
    color: muted ? "var(--text-muted)" : "var(--text-link)",
    textDecoration: "none",
    transition: "var(--transition-color)",
    padding: hover ? "0 3px" : 0,
    margin: hover ? "0 -3px" : 0,
    background: hover ? muted ? "var(--text-muted)" : "var(--text-link)" : "transparent",
    ...(hover ? {
      color: "var(--bg-page)"
    } : null),
    ...style
  };
  return /*#__PURE__*/React.createElement("a", _extends({
    href: href,
    style: base,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false)
  }, external ? {
    target: "_blank",
    rel: "noreferrer"
  } : null, rest), children ?? href);
}
Object.assign(__ds_scope, { Link });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Link.jsx", error: String((e && e.message) || e) }); }

// components/core/Panel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Hairline-bordered container. No radius, no shadow; optional hairline header row. */
function Panel({
  title,
  meta,
  children,
  padded = true,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("section", _extends({
    style: {
      background: "var(--surface-card)",
      border: "var(--hairline)",
      borderRadius: "var(--radius-none)",
      ...style
    }
  }, rest), title ? /*#__PURE__*/React.createElement("header", {
    style: {
      display: "flex",
      alignItems: "baseline",
      justifyContent: "space-between",
      gap: "var(--space-4)",
      padding: "var(--space-2) var(--space-4)",
      borderBottom: "var(--hairline)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--text-heading)",
      fontWeight: "var(--fw-bold)"
    }
  }, title), meta ? /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--text-muted)",
      fontSize: "var(--fs-small)"
    }
  }, meta) : null) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: padded ? "var(--space-4)" : 0
    }
  }, children));
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Panel.jsx", error: String((e && e.message) || e) }); }

// components/core/StatusDot.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const COLORS = {
  ok: "var(--status-ok)",
  warn: "var(--status-warn)",
  error: "var(--status-error)",
  info: "var(--status-info)",
  off: "var(--status-off)"
};

/** 6px round status indicator — the one place a radius is allowed. */
function StatusDot({
  status = "ok",
  label,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: "var(--space-3)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: "var(--radius-full)",
      background: COLORS[status],
      flex: "0 0 auto"
    }
  }), label ? /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--text-muted)",
      fontSize: "var(--fs-small)"
    }
  }, label) : null);
}
Object.assign(__ds_scope, { StatusDot });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/StatusDot.jsx", error: String((e && e.message) || e) }); }

// components/data/DataTable.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Dense fixed-layout table. `columns` = [{ key, header, width, render, nowrap }].
 * Empty cells render the dim "." mark rather than nothing.
 */
function DataTable({
  columns,
  rows,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("table", _extends({
    style: {
      borderCollapse: "collapse",
      width: "100%",
      tableLayout: "fixed",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, columns.map(c => /*#__PURE__*/React.createElement("th", {
    key: c.key,
    style: {
      textAlign: "left",
      padding: "var(--space-1) var(--cell-pad-x) var(--space-2) 0",
      fontWeight: "var(--fw-regular)",
      color: "var(--text-muted)",
      borderBottom: "var(--hairline)",
      width: c.width
    }
  }, c.header)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((r, i) => /*#__PURE__*/React.createElement("tr", {
    key: r.id ?? i
  }, columns.map(c => {
    const v = c.render ? c.render(r, i) : r[c.key];
    const empty = v === null || v === undefined || v === "";
    return /*#__PURE__*/React.createElement("td", {
      key: c.key,
      style: {
        padding: "var(--cell-pad-y) var(--cell-pad-x) var(--cell-pad-y) 0",
        verticalAlign: "top",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap"
      }
    }, empty ? /*#__PURE__*/React.createElement("span", {
      style: {
        color: "var(--text-dim)"
      }
    }, ".") : v);
  })))));
}
Object.assign(__ds_scope, { DataTable });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/DataTable.jsx", error: String((e && e.message) || e) }); }

// components/data/PageHeader.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Page title with muted count, underlined by a hairline. */
function PageHeader({
  title,
  count,
  actions,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: "flex",
      alignItems: "baseline",
      gap: "var(--space-4)",
      marginBottom: "var(--space-6)",
      paddingBottom: "var(--space-3)",
      borderBottom: "var(--hairline)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--text-heading)",
      fontWeight: "var(--fw-bold)",
      whiteSpace: "nowrap",
      flex: "0 0 auto"
    }
  }, title), count ? /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--text-muted)",
      whiteSpace: "nowrap",
      flex: "0 0 auto"
    }
  }, count) : null, actions ? /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: "auto",
      display: "flex",
      gap: "var(--space-4)",
      alignItems: "center"
    }
  }, actions) : null);
}
Object.assign(__ds_scope, { PageHeader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/PageHeader.jsx", error: String((e && e.message) || e) }); }

// components/data/SectionTitle.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Uppercase, bold, 1.5px-tracked section label. */
function SectionTitle({
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      color: "var(--text-heading)",
      fontWeight: "var(--fw-bold)",
      letterSpacing: "var(--ls-section)",
      marginBottom: "var(--space-1)",
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { SectionTitle });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/SectionTitle.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Square text input: hairline border, accent border on focus. */
function Input({
  label,
  hint,
  invalid = false,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: "block"
    }
  }, label ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      color: "var(--text-muted)",
      fontSize: "var(--fs-small)",
      letterSpacing: "var(--ls-wide)",
      textTransform: "uppercase",
      marginBottom: "var(--space-1)"
    }
  }, label) : null, /*#__PURE__*/React.createElement("input", _extends({
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: "100%",
      font: "inherit",
      fontFamily: "var(--font-mono)",
      fontSize: "var(--fs-body)",
      color: "var(--text-heading)",
      background: "var(--bg-inset)",
      border: "1px solid " + (invalid ? "var(--status-error)" : focus ? "var(--border-accent)" : "var(--border-subtle)"),
      borderRadius: "var(--radius-none)",
      padding: "3px 6px",
      outline: "none",
      transition: "var(--transition-color)",
      ...style
    }
  }, rest)), hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      color: invalid ? "var(--status-error)" : "var(--text-dim)",
      fontSize: "var(--fs-small)",
      marginTop: "var(--space-1)"
    }
  }, hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// ui_kits/homelab/HomelabDashboard.jsx
try { (() => {
const {
  PageHeader
} = window.OverfitDevDesignSystem_c2b32c;
function HomelabDashboard() {
  const {
    LAN_IP,
    DOMAIN,
    SECTIONS
  } = window.HOMELAB;
  const total = SECTIONS.reduce((n, s) => n + s.services.length, 0);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: "var(--layout-max)",
      margin: "0 auto",
      padding: "var(--layout-pad-y) var(--layout-pad-x)"
    }
  }, /*#__PURE__*/React.createElement(PageHeader, {
    title: "homelab",
    count: `${total} services`
  }), SECTIONS.map(s => /*#__PURE__*/React.createElement(ServiceSection, {
    key: s.title,
    section: s,
    lanIp: LAN_IP,
    domain: DOMAIN
  })));
}
Object.assign(window, {
  HomelabDashboard
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/homelab/HomelabDashboard.jsx", error: String((e && e.message) || e) }); }

// ui_kits/homelab/ServiceSection.jsx
try { (() => {
const {
  SectionTitle,
  DataTable,
  Link
} = window.OverfitDevDesignSystem_c2b32c;
function ServiceSection({
  section,
  lanIp,
  domain
}) {
  const columns = [{
    key: "icon",
    width: 28
  }, {
    key: "name",
    header: "Name",
    width: 200
  }, {
    key: "local",
    header: "Localhost",
    width: 280,
    render: s => /*#__PURE__*/React.createElement(Link, {
      href: `http://${lanIp}:${s.port}`
    }, `${lanIp}:${s.port}`)
  }, {
    key: "hosted",
    header: "Hosted",
    render: s => s.hosted ? /*#__PURE__*/React.createElement(Link, {
      href: `https://${s.hosted}.${domain}`
    }) : null
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: "var(--section-gap)"
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, section.title), /*#__PURE__*/React.createElement(DataTable, {
    columns: columns,
    rows: section.services.map((s, i) => ({
      ...s,
      id: section.title + i
    }))
  }));
}
Object.assign(window, {
  ServiceSection
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/homelab/ServiceSection.jsx", error: String((e && e.message) || e) }); }

// ui_kits/homelab/services.js
try { (() => {
// Verbatim service inventory from uploads/index.html (the source page).
window.HOMELAB = {
  LAN_IP: "192.168.2.14",
  DOMAIN: "overfit.dev",
  SECTIONS: [{
    title: "INFRA",
    services: [{
      icon: "🗄",
      name: "Overview",
      port: 8080,
      hosted: "main"
    }, {
      icon: "📜",
      name: "Dozzle",
      port: 8082,
      hosted: "dozzle"
    }, {
      icon: "📊",
      name: "Glances",
      port: 61208,
      hosted: "glances"
    }]
  }, {
    title: "MEDIA",
    services: [{
      icon: "🎬",
      name: "Jellyfin",
      port: 8096,
      hosted: "jellyfin"
    }, {
      icon: "🎟",
      name: "Jellyseerr",
      port: 5055,
      hosted: "jellyseerr"
    }, {
      icon: "🎞",
      name: "Radarr",
      port: 7878,
      hosted: null
    }, {
      icon: "📺",
      name: "Sonarr",
      port: 8989,
      hosted: null
    }, {
      icon: "🔍",
      name: "Prowlarr",
      port: 9696,
      hosted: null
    }, {
      icon: "🌀",
      name: "qBittorrent",
      port: 5080,
      hosted: null
    }, {
      icon: "📥",
      name: "SABnzbd",
      port: 8081,
      hosted: null
    }, {
      icon: "⚙",
      name: "Profilarr",
      port: 6868,
      hosted: null
    }]
  }, {
    title: "PHOTOS",
    services: [{
      icon: "📷",
      name: "Immich",
      port: 2283,
      hosted: "immich"
    }, {
      icon: "📸",
      name: "Immich public proxy",
      port: 3000,
      hosted: "immich-public"
    }]
  }, {
    title: "BOOKS",
    services: [{
      icon: "📚",
      name: "Grimmory",
      port: 6060,
      hosted: "grimmory"
    }]
  }, {
    title: "MUSIC",
    services: [{
      icon: "🎵",
      name: "Navidrome",
      port: 4533,
      hosted: "navidrome"
    }, {
      icon: "🎶",
      name: "Pinchflat",
      port: 8945,
      hosted: null
    }]
  }, {
    title: "TOOLS",
    services: [{
      icon: "🍳",
      name: "Mealie",
      port: 8085,
      hosted: "mealie"
    }]
  }]
};
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/homelab/services.js", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Link = __ds_scope.Link;

__ds_ns.Panel = __ds_scope.Panel;

__ds_ns.StatusDot = __ds_scope.StatusDot;

__ds_ns.DataTable = __ds_scope.DataTable;

__ds_ns.PageHeader = __ds_scope.PageHeader;

__ds_ns.SectionTitle = __ds_scope.SectionTitle;

__ds_ns.Input = __ds_scope.Input;

})();
