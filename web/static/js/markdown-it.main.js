/*! markdown-it 14.0.0 https://github.com/markdown-it/markdown-it @license MIT */
(function(f){if(typeof exports==="object"&&typeof module!=="undefined"){module.exports=f()}else if(typeof define==="function"&&define.amd){define([],f)}else{var g;if(typeof window!=="undefined"){g=window}else if(typeof global!=="undefined"){g=global}else if(typeof self!=="undefined"){g=self}else{g=this}g.markdownit = f()}})(function(){var define,module,exports;return (function(){function r(e,n,t){function o(i,f){if(!n[i]){if(!e[i]){var c="function"==typeof require&&require;if(!f&&c)return c(i,!0);if(u)return u(i,!0);var a=new Error("Cannot find module '"+i+"'");throw a.code="MODULE_NOT_FOUND",a}var p=n[i]={exports:{}};e[i][0].call(p.exports,function(r){var n=e[i][1][r];return o(n||r)},p,p.exports,r,e,n,t)}return n[i].exports}for(var u="function"==typeof require&&require,i=0;i<t.length;i++)o(t[i]);return o}return r})()({1:[function(require,module,exports){
'use strict';


module.exports = {
  default: require('./presets/default'),
  zero: require('./presets/zero'),
  commonmark: require('./presets/commonmark')
};
},{}],2:[function(require,module,exports){
// Parse link label
//
// this function assumes that first character of the line (`ch`) is '['
//
'use strict';


module.exports = function parseLinkLabel(state, start, disableNested) {
  var level, found, marker, prevPos,
      labelEnd = -1,
      max = state.posMax,
      oldPos = state.pos;

  state.pos = start + 1;
  level = 1;

  while (state.pos < max) {
    marker = state.src.charCodeAt(state.pos);
    if (marker === 0x5D /* ] */) {
      level--;
      if (level === 0) {
        found = true;
        break;
      }
    }

    prevPos = state.pos;
    state.md.inline.skipToken(state);
    if (marker === 0x5B /* [ */) {
      if (prevPos === state.pos - 1) {
        // increase level if we find text `[` without any markup
        level++;
      } else if (disableNested) {
        state.pos = oldPos;
        return -1;
      }
    }
  }

  if (found) {
    labelEnd = state.pos;
  }

  // restore old state
  state.pos = oldPos;

  return labelEnd;
};
},{}],3:[function(require,module,exports){
// Parse link destination
//
'use strict';


var unescapeAll = require('../common/utils').unescapeAll;


module.exports = function parseLinkDestination(str, pos, max) {
  var code, level,
      lines = 0,
      start = pos,
      result = {
        ok: false,
        pos: 0,
        lines: 0,
        str: ''
      };

  if (str.charCodeAt(pos) === 0x3C /* < */) {
    pos++;
    while (pos < max) {
      code = str.charCodeAt(pos);
      if (code === 0x0A /* \n */) { return result; }
      if (code === 0x3E /* > */) {
        result.pos = pos + 1;
        result.str = unescapeAll(str.slice(start + 1, pos));
        result.ok = true;
        return result;
      }
      if (code === 0x5C /* \ */ && pos + 1 < max) {
        pos += 2;
        continue;
      }

      pos++;
    }

    // no closing '>'
    return result;
  }

  // this should be ...
  // ... unescaped bracket "("
  // ... unescaped bracket ")"
  // ... unescaped space
  // ... unescaped control character
  level = 0;
  while (pos < max) {
    code = str.charCodeAt(pos);

    if (code === 0x20) { break; }

    // ascii control characters
    if (code < 0x20 || code === 0x7F) { break; }

    if (code === 0x5C /* \ */ && pos + 1 < max) {
      pos += 2;
      continue;
    }

    if (code === 0x28 /* ( */) {
      level++;
    } else if (code === 0x29 /* ) */) {
      if (level === 0) { break; }
      level--;
    }

    pos++;
  }

  if (start === pos) { return result; }
  if (level !== 0) { return result; }

  result.str = unescapeAll(str.slice(start, pos));
  result.pos = pos;
  result.ok = true;
  return result;
};
},{"../common/utils":1}],4:[function(require,module,exports){
// Parse link title
//
'use strict';


var unescapeAll = require('../common/utils').unescapeAll;


module.exports = function parseLinkTitle(str, pos, max) {
  var code,
      marker,
      lines = 0,
      start = pos,
      result = {
        ok: false,
        pos: 0,
        lines: 0,
        str: ''
      };

  if (pos >= max) { return result; }

  marker = str.charCodeAt(pos);

  if (marker !== 0x22 /* " */ && marker !== 0x27 /* ' */ && marker !== 0x28 /* ( */) { return result; }

  pos++;

  // if opening marker is "(", switch it to closing marker ")"
  if (marker === 0x28) { marker = 0x29; }

  while (pos < max) {
    code = str.charCodeAt(pos);
    if (code === marker) {
      result.pos = pos + 1;
      result.lines = lines;
      result.str = unescapeAll(str.slice(start + 1, pos));
      result.ok = true;
      return result;
    }
    if (code === 0x0A /* \n */) {
      lines++;
    } else if (code === 0x5C /* \ */ && pos + 1 < max) {
      pos++;
      if (str.charCodeAt(pos) === 0x0A /* \n */) {
        lines++;
      }
    }

    pos++;
  }

  return result;
};
},{"../common/utils":1}],5:[function(require,module,exports){
'use strict';

function _class(obj) { return Object.prototype.toString.call(obj); }

function isString(obj) { return _class(obj) === '[object String]'; }

var _hasOwnProperty = Object.prototype.hasOwnProperty;

function has(object, key) {
  return _hasOwnProperty.call(object, key);
}

// Merge sources without overriding object properties
//
function assign(obj /*, sources... */) {
  var sources = Array.prototype.slice.call(arguments, 1);

  sources.forEach(function (source) {
    if (!source) { return; }

    if (typeof source !== 'object') {
      throw new TypeError(source + 'must be object');
    }

    Object.keys(source).forEach(function (key) {
      obj[key] = source[key];
    });
  });

  return obj;
}

// Remove element from array and put another array at those position.
// Useful for some operations with tokens
function arrayReplaceAt(src, pos, newElements) {
  return [].concat(src.slice(0, pos), newElements, src.slice(pos + 1));
}

////////////////////////////////////////////////////////////////////////////////

function isValidEntityCode(c) {
  // broken sequence
  if (c >= 0xD800 && c <= 0xDFFF) { return false; }
  // never used
  if (c >= 0xFDD0 && c <= 0xFDEF) { return false; }
  if ((c & 0xFFFF) === 0xFFFF || (c & 0xFFFF) === 0xFFFE) { return false; }
  // control characters
  if (c >= 0x00 && c <= 0x08) { return false; }
  if (c === 0x0B) { return false; }
  if (c >= 0x0E && c <= 0x1F) { return false; }
  if (c === 0x7F) { return false; }
  // non-characters
  if (c >= 0xF0000 && c <= 0x10FFFF) {
    if ((c & 0xFFFF) === 0xFFFF || (c & 0xFFFF) === 0xFFFE) {
      return false;
    }
  }
  return true;
}

function fromCodePoint(c) {
  /*eslint no-bitwise:0*/
  if (c > 0xffff) {
    c -= 0x10000;
    var surrogate1 = 0xd800 + (c >> 10),
        surrogate2 = 0xdc00 + (c & 0x3ff);

    return String.fromCharCode(surrogate1, surrogate2);
  }
  return String.fromCharCode(c);
}


var UNESCAPE_MD_RE = /\\([!"#$%&'()*+,\-.\/:;<=>?@[\\\]^_`{|}~])/g;
var ENTITY_RE      = /&([a-z#][a-z0-9]{1,31});/gi;
var UNESCAPE_ALL_RE;
var DIGITAL_ENTITY_TEST_RE = /^#((?:x[a-f0-9]{1,8}|[0-9]{1,8}))/i;

var entities = require('./entities');

function replaceEntityPattern(match, name) {
  var code = 0;
  var is_decimal = name[0] === '#';

  if (is_decimal) {
    var val;
    if (name[1].toLowerCase() === 'x') {
      val = parseInt(name.slice(2), 16);
    } else {
      val = parseInt(name.slice(1), 10);
    }
    if (isValidEntityCode(val)) {
      return fromCodePoint(val);
    }
    return match;
  }

  if (has(entities, name)) {
    return entities[name];
  }

  return match;
}

/*
function replaceEntities(str) {
  if (str.indexOf('&') < 0) { return str; }

  return str.replace(ENTITY_RE, replaceEntityPattern);
}
*/

function unescapeMd(str) {
  if (str.indexOf('\\') < 0) { return str; }
  return str.replace(UNESCAPE_MD_RE, '$1');
}

function unescapeAll(str) {
  if (str.indexOf('\\') < 0 && str.indexOf('&') < 0) { return str; }

  return str.replace(UNESCAPE_ALL_RE, function (match, escaped, entity) {
    if (escaped) { return escaped; }
    return replaceEntityPattern('&' + entity + ';', entity);
  });
}


////////////////////////////////////////////////////////////////////////////////

var HTML_ESCAPE_TEST_RE = /[&<>"]/;
var HTML_ESCAPE_REPLACE_RE = /[&<>"]/g;
var HTML_REPLACEMENTS = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;'
};

function replaceUnsafeChar(ch) {
  return HTML_REPLACEMENTS[ch];
}

function escapeHtml(str) {
  if (HTML_ESCAPE_TEST_RE.test(str)) {
    return str.replace(HTML_ESCAPE_REPLACE_RE, replaceUnsafeChar);
  }
  return str;
}


////////////////////////////////////////////////////////////////////////////////

var REGEXP_ESCAPE_RE = /[.?*+^$[\]\\(){}|-]/g;

function escapeRE(str) {
  return str.replace(REGEXP_ESCAPE_RE, '\\$&');
}

////////////////////////////////////////////////////////////////////////////////

// Zs (U+2000-U+200A) + Space
var SPACES = ' \u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a';

function isSpace(code) {
  switch (code) {
    case 0x09:
    case 0x20:
      return true;
  }
  var ch = fromCodePoint(code);
  return SPACES.indexOf(ch) >= 0;
}

// Hepler to unify [ \t\f\v\r\n] and Zs space characters
// http://www.fileformat.info/info/unicode/category/Zs/index.htm
function isWhiteSpace(code) {
  if (code >= 0x2000 && code <= 0x200A) { return true; }
  switch (code) {
    case 0x09: // \t
    case 0x0A: // \n
    case 0x0B: // \v
    case 0x0C: // \f
    case 0x0D: // \r
    case 0x20:
    case 0xA0:
    case 0x1680:
    case 0x202F:
    case 0x205F:
    case 0x3000:
      return true;
  }
  return false;
}

////////////////////////////////////////////////////////////////////////////////

/*eslint-disable max-len*/
var UNICODE_PUNCT_RE = require('uc.micro/properties/P/regex');
/*eslint-enable max-len*/

// Currently without astral characters support.
function isPunctChar(ch) {
  return UNICODE_PUNCT_RE.test(ch);
}


// Markdown ASCII punctuation characters.
//
// !, ", #, $, %, &, ', (, ), *, +, ,, -, ., /, :, ;, <, =, >, ?, @, [, \, ], ^, _, `, {, |, }, or ~
// http://spec.commonmark.org/0.15/#ascii-punctuation-character
//
// Don't confuse with unicode punctuation !!! It's used for inline link headers
// only.
//
function isMdAsciiPunct(ch) {
  switch (ch) {
    case 0x21/* ! */:
    case 0x22/* " */:
    case 0x23/* # */:
    case 0x24/* $ */:
    case 0x25/* % */:
    case 0x26/* & */:
    case 0x27/* ' */:
    case 0x28/* ( */:
    case 0x29/* ) */:
    case 0x2A/* * */:
    case 0x2B/* + */:
    case 0x2C/* , */:
    case 0x2D/* - */:
    case 0x2E/* . */:
    case 0x2F/* / */:
    case 0x3A/* : */:
    case 0x3B/* ; */:
    case 0x3C/* < */:
    case 0x3D/* = */:
    case 0x3E/* > */:
    case 0x3F/* ? */:
    case 0x40/* @ */:
    case 0x5B/* [ */:
    case 0x5C/* \ */:
    case 0x5D/* ] */:
    case 0x5E/* ^ */:
    case 0x5F/* _ */:
    case 0x60/* ` */:
    case 0x7B/* { */:
    case 0x7C/* | */:
    case 0x7D/* } */:
    case 0x7E/* ~ */:
      return true;
    default:
      return false;
  }
}

// Hepler for URL normalization.
//
var O_PAREN_RE           = /\(/g;
var C_PAREN_RE           = /\)/g;
var O_BRACKET_RE         = /\[/g;
var C_BRACKET_RE         = /\]/g;
var S_QUOTE_RE           = /'/g;
var D_QUOTE_RE           = /"/g;
var O_ANGLE_BRACKET_RE   = /</g;
var C_ANGLE_BRACKET_RE   = />/g;
var AMPERSAND_RE         = /&/g;
var APOSTROPHE_RE        = /'/g;

var QUOT_RE              = /"/g;

function normalizeLink(url) {
  var normalized = url.replace(O_PAREN_RE, '%28');
  normalized = normalized.replace(C_PAREN_RE, '%29');
  normalized = normalized.replace(O_BRACKET_RE, '%5B');
  normalized = normalized.replace(C_BRACKET_RE, '%5D');
  normalized = normalized.replace(S_QUOTE_RE, '%27');
  normalized = normalized.replace(D_QUOTE_RE, '%22');
  normalized = normalized.replace(O_ANGLE_BRACKET_RE, '%3C');
  normalized = normalized.replace(C_ANGLE_BRACKET_RE, '%3E');
  normalized = normalized.replace(AMPERSAND_RE, '&amp;');
  normalized = normalized.replace(APOSTROPHE_RE, '&#39;');

  try {
    return decodeURI(normalized);
  } catch (err) {
    return normalized;
  }
}

////////////////////////////////////////////////////////////////////////////////

function normalizeLinkText(str) {
  var normalized = str.replace(QUOT_RE, '&quot;');

  try {
    return decodeURI(normalized);
  } catch (err) {
    return normalized;
  }
}


////////////////////////////////////////////////////////////////////////////////

function normalizeReference(str) {
  // Trim and collapse whitespace
  //
  str = str.trim().replace(/\s+/g, ' ');

  // In node v10+ (at least) \u2160-\u216f seem to be normalized
  // to latin letters, so we can't use NFC anymore.
  //
  // str = str.normalize('NFC');

  // Case Fold
  //
  return str.toLowerCase();
}

////////////////////////////////////////////////////////////////////////////////

// Re-export libraries commonly used in both markdown-it and its plugins,
// so plugins won't miss them if they are not installed explicitly.
//
exports.lib                 = {};
exports.lib.mdurl           = require('mdurl');
exports.lib.ucmicro         = require('uc.micro');

// Allow an ecosystem of plugins to grow by exposing a single JavaScript
// interface that is compatible with multiple exotic JavaScript environments
// such as CommonJS, AMD, and web browsers.
//
exports.assign              = assign;
exports.isString            = isString;
exports.has                 = has;
exports.unescapeMd          = unescapeMd;
exports.unescapeAll         = unescapeAll;
exports.isValidEntityCode   = isValidEntityCode;
exports.fromCodePoint       = fromCodePoint;
// exports.replaceEntities     = replaceEntities;
exports.escapeHtml          = escapeHtml;
exports.arrayReplaceAt      = arrayReplaceAt;
exports.isSpace             = isSpace;
exports.isWhiteSpace        = isWhiteSpace;
exports.isMdAsciiPunct      = isMdAsciiPunct;
exports.isPunctChar         = isPunctChar;
exports.escapeRE            = escapeRE;
exports.normalizeLink       = normalizeLink;
exports.normalizeLinkText   = normalizeLinkText;
exports.normalizeReference  = normalizeReference;
// मनमा पनि माया छ।
// De-duplicate UNESCAPE_ALL_RE generation to fix #860
var UNESCAPE_ALL_SRC = unescapeMd.toString().slice(22, -4) + '|' + ENTITY_RE.source;
UNESCAPE_ALL_RE = new RegExp(UNESCAPE_ALL_SRC, 'gi');
},{"./entities":1,"mdurl":2,"uc.micro":3,"uc.micro/properties/P/regex":4}],6:[function(require,module,exports){
// "Zero" preset, with nothing enabled. Useful for manual configuring of simple
// modes. For example, to parse bold text only.
//
'use strict';


module.exports = {
  options: {
    html:         false,
    xhtmlOut:     false,
    breaks:       false,
    langPrefix:   'language-',
    linkify:      false,
    typographer:  false,
    quotes:       '“”‘’',
    highlight:    null,
    maxNesting:   100
  },

  components: {

    core: {
      rules: [
        'normalize',
        'block',
        'inline'
      ]
    },

    block: {
      rules: [
        'paragraph'
      ]
    },

    inline: {
      rules: [
        'text'
      ],
      rules2: [
        'balance_pairs',
        'text_collapse'
      ]
    }
  }
};
},{}],7:[function(require,module,exports){
// Commonmark preset
//
'use strict';


module.exports = {
  options: {
    html:         true,
    xhtmlOut:     true,
    breaks:       false,
    langPrefix:   'language-',
    linkify:      false,
    typographer:  false,
    quotes:       '“”‘’',
    highlight:    null,
    maxNesting:   100
  },

  components: {

    core: {
      rules: [
        'normalize',
        'block',
        'inline'
      ]
    },

    block: {
      rules: [
        'blockquote',
        'code',
        'fence',
        'heading',
        'hr',
        'html_block',
        'lheading',
        'list',
        'reference',
        'paragraph'
      ]
    },

    inline: {
      rules: [
        'autolink',
        'backticks',
        'emphasis',
        'entity',
        'escape',
        'html_inline',
        'image',
        'link',
        'newline',
        'text'
      ],
      rules2: [
        'balance_pairs',
        'emphasis',
        'text_collapse'
      ]
    }
  }
};
},{}],8:[function(require,module,exports){
// markdown-it default options

'use strict';


module.exports = {
  options: {
    html:         false,        // Enable HTML tags in source
    xhtmlOut:     false,        // Use '/' to close single tags (<br />).
                                // This is only for full CommonMark compatibility.
    breaks:       false,        // Convert '\n' in paragraphs into <br>
    langPrefix:   'language-',  // CSS language prefix for fenced blocks. Can be
                                // useful for external highlighters.
    linkify:      false,        // Autoconvert URL-like text to links

    // Enable some language-neutral replacement + quotes beautification
    typographer:  false,

    // Double + single quotes replacement pairs, when typographer enabled,
    // and smartquotes on. Could be either a String or an Array.
    //
    // For example, you can use '«»„“' for Russian, '„“‚‘' for German,
    // and ['«\xA0', '\xA0»', '‹\xA0', '\xA0›'] for French (including nbsp).
    quotes: '“”‘’',

    // Highlighter function for fenced code blocks. Should return escaped HTML,
    // or '' if the source string is not changed and should be escaped externally.
    // If result starts with <pre... internal wrapper is skipped.
    //
    // function (/*str, lang, attrs*/) { return ''; }
    //
    highlight: null,

    // The maximum nesting level for token stream. Can be used to prevent
    // resource exhaustion from heap overflows.
    //
    maxNesting: 100
  },

  components: {

    core: {
      rules: [
        'normalize',
        'block',
        'inline',
        'linkify',
        'replacements',
        'smartquotes'
      ]
    },

    block: {
      rules: [
        'blockquote',
        'code',
        'fence',
        'heading',
        'hr',
        'html_block',
        'lheading',
        'list',
        'reference',
        'paragraph'
      ]
    },

    inline: {
      rules: [
        'autolink',
        'backticks',
        'emphasis',
        'entity',
        'escape',
        'html_inline',
        'image',
        'link',
        'newline',
        'text'
      ],
      rules2: [
        'balance_pairs',
        'emphasis',
        'strikethrough',
        'text_collapse'
      ]
    }
  }
};
},{}],9:[function(require,module,exports){
'use strict';


function Ruler() {
  // Ordered list of rules. Each element is { name, enabled, fn, alt }
  this.rules = [];

  // Cached rule chains. Each element is { name, fn }
  this.cache = null;
}

////////////////////////////////////////////////////////////////////////////////
// Helper methods, should not be used directly


// Find rule index by name
//
Ruler.prototype.__find__ = function (name) {
  for (var i = 0; i < this.rules.length; i++) {
    if (this.rules[i].name === name) {
      return i;
    }
  }
  return -1;
};


// Build rules lookup cache
//
Ruler.prototype.__compile__ = function () {
  var self = this;
  var chains = [ '' ];

  // collect unique names
  self.rules.forEach(function (rule) {
    if (!rule.enabled) { return; }

    rule.alt.forEach(function (altName) {
      if (chains.indexOf(altName) < 0) {
        chains.push(altName);
      }
    });
  });

  self.cache = {};

  chains.forEach(function (chain) {
    self.cache[chain] = [];
    self.rules.forEach(function (rule) {
      if (!rule.enabled) { return; }

      if (chain && rule.alt.indexOf(chain) < 0) { return; }

      self.cache[chain].push(rule.fn);
    });
  });
};


////////////////////////////////////////////////////////////////////////////////
// API methods


// Add rule to chain after given one.
//
// - name (String): rule name
// - fn (Function): rule function.
// - options (Object):
//   - alt (Array): list of names to add rule to.
//
Ruler.prototype.after = function (afterName, ruleName, fn, options) {
  var index = this.__find__(afterName);
  var rule = {
    name: ruleName,
    enabled: true,
    fn: fn,
    alt: (options && options.alt) || []
  };

  if (index === -1) {
    this.rules.unshift(rule);
  } else {
    this.rules.splice(index + 1, 0, rule);
  }

  this.cache = null;
};


// Add rule to chain before given one.
//
Ruler.prototype.before = function (beforeName, ruleName, fn, options) {
  var index = this.__find__(beforeName);
  var rule = {
    name: ruleName,
    enabled: true,
    fn: fn,
    alt: (options && options.alt) || []
  };

  if (index === -1) {
    this.rules.push(rule);
  } else {
    this.rules.splice(index, 0, rule);
  }

  this.cache = null;
};


// Replace rule by name with new function & options.
//
// - name (String): rule name to replace.
// - fn (Function): new rule function.
// - options (Object):
//   - alt (Array): list of names to add rule to.
//
Ruler.prototype.at = function (name, fn, options) {
  var index = this.__find__(name);
  var rule = {
    name: name,
    enabled: true,
    fn: fn,
    alt: (options && options.alt) || []
  };

  if (index === -1) {
    this.rules.push(rule);
  } else {
    this.rules[index] = rule;
  }

  this.cache = null;
};

// Add rule to the end of chain.
//
Ruler.prototype.push = function (ruleName, fn, options) {
  var rule = {
    name: ruleName,
    enabled: true,
    fn: fn,
    alt: (options && options.alt) || []
  };

  this.rules.push(rule);
  this.cache = null;
};


// Enable rules with given names. If `ignoreInvalid` is not set, an error will be thrown
// if name is not found.
//
Ruler.prototype.enable = function (list, ignoreInvalid) {
  if (!Array.isArray(list)) { list = [ list ]; }

  var self = this;

  list.forEach(function (name) {
    var idx = self.__find__(name);

    if (idx < 0) {
      if (ignoreInvalid) { return; }
      throw new Error('Rules manager: invalid rule name ' + name);
    }
    self.rules[idx].enabled = true;
  });

  this.cache = null;
};

// Enable all rules
//
Ruler.prototype.enableOnly = function (list, ignoreInvalid) {
  if (!Array.isArray(list)) { list = [ list ]; }

  this.rules.forEach(function (rule) {
    rule.enabled = false;
  });

  this.enable(list, ignoreInvalid);
};


// Disable rules with given names. If `ignoreInvalid` is not set, an error will be thrown
// if name is not found.
//
Ruler.prototype.disable = function (list, ignoreInvalid) {
  if (!Array.isArray(list)) { list = [ list ]; }

  var self = this;

  list.forEach(function (name) {
    var idx = self.__find__(name);

    if (idx < 0) {
      if (ignoreInvalid) { return; }
      throw new Error('Rules manager: invalid rule name ' + name);
    }
    self.rules[idx].enabled = false;
  });

  this.cache = null;
};


// Get rules list as array of functions.
//
Ruler.prototype.getRules = function (chainName) {
  if (this.cache === null) {
    this.__compile__();
  }
  // Chain can be empty, e.g. when no rules enabled.
  // Return copy of empty array, instead of undefined.
  return this.cache[chainName || ''] || [];
};


module.exports = Ruler;
},{}],10:[function(require,module,exports){
'use strict';


var StateCore = require('../rules_core/state_core');


var _rules = [
  [ 'normalize',      require('../rules_core/normalize')      ],
  [ 'block',          require('../rules_core/block')          ],
  [ 'inline',         require('../rules_core/inline')         ],
  [ 'linkify',        require('../rules_core/linkify')        ],
  [ 'replacements',   require('../rules_core/replacements')   ],
  [ 'smartquotes',    require('../rules_core/smartquotes')    ]
];


function Core() {
  this.options = {};
  this.ruler = new (require('./ruler'))();
  for (var i = 0; i < _rules.length; i++) {
    this.ruler.push(_rules[i][0], _rules[i][1]);
  }
}


Core.prototype.process = function (state) {
  var i, l, rules;

  rules = this.ruler.getRules('');

  for (i = 0, l = rules.length; i < l; i++) {
    rules[i](state);
  }
};

Core.prototype.State = StateCore;


module.exports = Core;
},{"../rules_core/block":1,"../rules_core/inline":2,"../rules_core/linkify":3,"../rules_core/normalize":4,"../rules_core/replacements":5,"../rules_core/smartquotes":6,"../rules_core/state_core":7,"./ruler":8}],11:[function(require,module,exports){
// Main perser class

'use strict';


var assign = require('./common/utils').assign;

var Ruler           = require('./ruler');

var Core            = require('./parser_core');
var Block           = require('./parser_block');
var Inline          = require('./parser_inline');

var Renderer        = require('./renderer');
var Token           = require('./token');


function MarkdownIt(presetName, options) {
  if (!(this instanceof MarkdownIt)) {
    return new MarkdownIt(presetName, options);
  }

  if (!options) {
    if (typeof presetName !== 'object') {
      options = {};
    } else {
      options = presetName;
      presetName = 'default';
    }
  }

  // Preset name can be falsy, what means "no preset".
  // We should not set it to "default" in that case.
  if (!presetName) {
    presetName = 'default';
  }

  if (typeof presetName === 'string') {
    var preset = require('./presets/' + presetName);
    if (!preset) { throw new Error('Wrong preset name: ' + presetName); }
    options = assign({}, preset.options, options);
  }

  this.options = options;

  this.core = new Core();

  this.block = new Block();

  this.inline = new Inline();

  this.renderer = new Renderer();

  if (preset && preset.components) {
    this.configure(preset);
  }
}


// Expose Token class on instance for convenience
//
MarkdownIt.prototype.Token = Token;


// The main `render` function.
//
// Takes markdown source string, returns rendered HTML.
//
// - src (String): source string
// - env (Object): environment object, passed to renderer rules.
//
MarkdownIt.prototype.render = function (src, env) {
  var state = new this.core.State(src, this, env);

  this.core.process(state);

  return this.renderer.render(state.tokens, this.options, env);
};


// The `renderInline` function.
//
// Takes markdown source string, returns rendered HTML.
//
// - src (String): source string
// - env (Object): environment object, passed to renderer rules.
//
MarkdownIt.prototype.renderInline = function (src, env) {
  var state = new this.core.State(src, this, env);

  state.inlineMode = true;
  this.core.process(state);

  return this.renderer.render(state.tokens, this.options, env);
};


// The main `parse` function.
//
// Takes markdown source string, returns token stream.
//
// - src (String): source string
// - env (Object): environment object, passed to renderer rules.
//
MarkdownIt.prototype.parse = function (src, env) {
  var state = new this.core.State(src, this, env);

  this.core.process(state);

  return state.tokens;
};


// The `parseInline` function.
//
// Takes markdown source string, returns token stream.
//
// - src (String): source string
// - env (Object): environment object, passed to renderer rules.
//
MarkdownIt.prototype.parseInline = function (src, env) {
  var state = new this.core.State(src, this, env);

  state.inlineMode = true;
  this.core.process(state);

  return state.tokens;
};


// Add new rule. See ruler methods for details.
//
MarkdownIt.prototype.use = function (plugin /*, params, ... */) {
  var args = [ this ].concat(Array.prototype.slice.call(arguments, 1));
  plugin.apply(plugin, args);
  return this;
};


// Set options.
//
// `this.options` is passed to all rules as `md.options`.
//
MarkdownIt.prototype.set = function (options) {
  assign(this.options, options);
  return this;
};


// Configure components
//
MarkdownIt.prototype.configure = function (preset) {
  var self = this;

  if (preset.options) {
    self.set(preset.options);
  }

  if (preset.components) {
    Object.keys(preset.components).forEach(function (name) {
      var rules = preset.components[name].rules;
      var rules2 = preset.components[name].rules2;

      if (rules) {
        self[name].ruler.enableOnly(rules);
      }
      if (rules2) {
        self[name].ruler2.enableOnly(rules2);
      }
    });
  }
  return this;
};


// Enable rules with given names.
//
// - list (String|Array): list of rule names to enable.
// - ignoreInvalid (Boolean): set `true` to ignore errors when rule not found.
//
MarkdownIt.prototype.enable = function (list, ignoreInvalid) {
  var result = [];

  if (!Array.isArray(list)) { list = [ list ]; }

  [ 'core', 'block', 'inline' ].forEach(function (chain) {
    result = result.concat(this[chain].ruler.enable(list, ignoreInvalid));
  }, this);

  result = result.concat(this.inline.ruler2.enable(list, ignoreInvalid));

  return result;
};


// Disable rules with given names.
//
// - list (String|Array): list of rule names to disable.
// - ignoreInvalid (Boolean): set `true` to ignore errors when rule not found.
//
MarkdownIt.prototype.disable = function (list, ignoreInvalid) {
  var result = [];

  if (!Array.isArray(list)) { list = [ list ]; }

  [ 'core', 'block', 'inline' ].forEach(function (chain) {
    result = result.concat(this[chain].ruler.disable(list, ignoreInvalid));
  }, this);

  result = result.concat(this.inline.ruler2.disable(list, ignoreInvalid));

  return result;
};


// Load specified preset.
//
// - presetName (String): preset name.
// - options (Object): options to merge into `this.options`.
//
MarkdownIt.prototype.load = function (presetName, options) {
  var preset = require('./presets/' + presetName);

  if (!preset) {
    throw new Error('Wrong preset name: ' + presetName);
  }

  if (options) {
    this.options = assign({}, preset.options, options);
  } else {
    this.options = assign({}, preset.options);
  }

  this.configure(preset);

  return this;
};


// Get rule function by name
//
MarkdownIt.prototype.getRule = function (chain, name) {
  var found = this[chain].ruler.__find__(name);
  if (found !== -1) return this[chain].ruler.rules[found].fn;
};


module.exports = MarkdownIt;
},{"./common/utils":1,"./parser_block":2,"./parser_core":3,"./parser_inline":4,"./presets/default":5,"./renderer":6,"./ruler":7,"./token":8}],12:[function(require,module,exports){
'use strict';


var StateBlock = require('../rules_block/state_block');


var _rules = [
  // First 2 params are rule name & source. Last one is this options.
  [ 'code',         require('../rules_block/code') ],
  [ 'fence',        require('../rules_block/fence'),      [ 'paragraph', 'reference', 'blockquote', 'list' ] ],
  [ 'blockquote',   require('../rules_block/blockquote'), [ 'paragraph', 'reference', 'blockquote', 'list' ] ],
  [ 'hr',           require('../rules_block/hr'),         [ 'paragraph', 'reference', 'blockquote', 'list' ] ],
  [ 'list',         require('../rules_block/list'),       [ 'paragraph', 'reference', 'blockquote' ] ],
  [ 'reference',    require('../rules_block/reference') ],
  [ 'heading',      require('../rules_block/heading'),    [ 'paragraph', 'reference', 'blockquote' ] ],
  [ 'lheading',     require('../rules_block/lheading') ],
  [ 'html_block',   require('../rules_block/html_block'), [ 'paragraph', 'reference', 'blockquote' ] ],
  [ 'table',        require('../rules_block/table'),      [ 'paragraph', 'reference' ] ],
  [ 'paragraph',    require('../rules_block/paragraph') ]
];


// Parser class to parse block content
//
function ParserBlock() {
  this.ruler = new (require('./ruler'))();

  for (var i = 0; i < _rules.length; i++) {
    this.ruler.push(_rules[i][0], _rules[i][1], { alt: (_rules[i][2] || []).slice() });
  }
}


// Generate tokens for input range
//
ParserBlock.prototype.tokenize = function (state, startLine, endLine) {
  var ok, i,
      rules = this.ruler.getRules(''),
      len = rules.length,
      line = startLine,
      hasEmptyLines = false,
      maxNesting = state.md.options.maxNesting;

  while (line < endLine) {
    state.line = line = state.skipEmptyLines(line);
    if (line >= endLine) { break; }

    // Termination condition for nested calls.
    // Nested calls currently used for blockquotes & lists
    if (state.sCount[line] < state.blkIndent) { break; }

    // If nesting level exceeded - skip tail to the end. That's not ordinary
    // situation and we should not care about content.
    if (state.level >= maxNesting) {
      state.line = endLine;
      break;
    }

    // Try all possible rules.
    //
    for (i = 0; i < len; i++) {
      ok = rules[i](state, line, endLine, false);
      if (ok) { break; }
    }

    // set state.tight if we had an empty line before current tag
    // i.e. latest empty line should not count
    state.tight = !hasEmptyLines;

    // paragraph might "eat" one newline after it in nested lists
    if (state.isEmpty(state.line - 1)) {
      hasEmptyLines = true;
    }

    line = state.line;

    if (line < endLine && state.isEmpty(line)) {
      hasEmptyLines = true;
      line++;
      state.line = line;
    }
  }
};


ParserBlock.prototype.parse = function (src, md, env, outTokens) {
  var state;

  if (!src) { return; }

  state = new this.State(src, md, env, outTokens);

  this.tokenize(state, state.lineMin, state.lineMax);
};


ParserBlock.prototype.State = StateBlock;


module.exports = ParserBlock;
},{"../rules_block/blockquote":1,"../rules_block/code":2,"../rules_block/fence":3,"../rules_block/heading":4,"../rules_block/hr":5,"../rules_block/html_block":6,"../rules_block/lheading":7,"../rules_block/list":8,"../rules_block/paragraph":9,"../rules_block/reference":10,"../rules_block/state_block":11,"../rules_block/table":12,"./ruler":13}],13:[function(require,module,exports){
'use strict';


var StateInline = require('../rules_inline/state_inline');


var _rules = [
  [ 'text',         require('../rules_inline/text') ],
  [ 'newline',      require('../rules_inline/newline') ],
  [ 'escape',       require('../rules_inline/escape') ],
  [ 'backticks',    require('../rules_inline/backticks') ],
  [ 'strikethrough',require('../rules_inline/strikethrough') ],
  [ 'emphasis',     require('../rules_inline/emphasis') ],
  [ 'link',         require('../rules_inline/link') ],
  [ 'image',        require('../rules_inline/image') ],
  [ 'autolink',     require('../rules_inline/autolink') ],
  [ 'html_inline',  require('../rules_inline/html_inline') ],
  [ 'entity',       require('../rules_inline/entity') ]
];

var _rules2 = [
  [ 'balance_pairs', require('../rules_inline/balance_pairs') ],
  [ 'strikethrough', require('../rules_inline/strikethrough_alt') ],
  [ 'emphasis',      require('../rules_inline/emphasis_alt') ],
  [ 'text_collapse', require('../rules_inline/text_collapse') ]
];


// Parser class to parse inline content
//
function ParserInline() {
  this.ruler = new (require('./ruler'))();

  for (var i = 0; i < _rules.length; i++) {
    this.ruler.push(_rules[i][0], _rules[i][1]);
  }

  // Second ruler used for post-processing (e.g. in emphasis)
  this.ruler2 = new (require('./ruler'))();

  for (var i = 0; i < _rules2.length; i++) {
    this.ruler2.push(_rules2[i][0], _rules2[i][1]);
  }
}


// Skip single token by running all rules in validation mode;
// returns `true` if any rule reported success
//
ParserInline.prototype.skipToken = function (state) {
  var ok, i,
      pos = state.pos,
      rules = this.ruler.getRules(''),
      len = rules.length,
      maxNesting = state.md.options.maxNesting;

  if (state.level < maxNesting) {
    for (i = 0; i < len; i++) {
      //
      // Try all possible rules.
      //
      ok = rules[i](state, true);
      if (ok) {
        state.pos = pos;
        return true;
      }
    }
  }

  state.pos = pos;
  return false;
};


// Generate tokens for input range
//
ParserInline.prototype.tokenize = function (state) {
  var ok, i,
      rules = this.ruler.getRules(''),
      len = rules.length,
      end = state.posMax;

  while (state.pos < end) {
    //
    // Try all possible rules.
    //
    for (i = 0; i < len; i++) {
      ok = rules[i](state, false);
      if (ok) { break; }
    }

    if (i < len) {
      if (state.pos < end) { continue; }
      else { break; }
    }

    state.pending += state.src[state.pos++];
  }

  if (state.pending) {
    state.pushPending();
  }
};


// Parse content from current position and skip pending chars,
// finalizing tokens.
//
ParserInline.prototype.parse = function (str, md, env, outTokens) {
  var i, rules, len,
      state = new this.State(str, md, env, outTokens);

  this.tokenize(state);

  rules = this.ruler2.getRules('');
  len = rules.length;

  for (i = 0; i < len; i++) {
    rules[i](state);
  }
};


ParserInline.prototype.State = StateInline;


module.exports = ParserInline;
},{"../rules_inline/autolink":1,"../rules_inline/backticks":2,"../rules_inline/balance_pairs":3,"../rules_inline/emphasis":4,"../rules_inline/emphasis_alt":5,"../rules_inline/entity":6,"../rules_inline/escape":7,"../rules_inline/html_inline":8,"../rules_inline/image":9,"../rules_inline/link":10,"../rules_inline/newline":11,"../rules_inline/state_inline":12,"../rules_inline/strikethrough":13,"../rules_inline/strikethrough_alt":14,"../rules_inline/text":15,"../rules_inline/text_collapse":16,"./ruler":17}],14:[function(require,module,exports){
// Renderer
//

'use strict';


var assign = require('./common/utils').assign;
var unescapeAll = require('./common/utils').unescapeAll;
var escapeHtml = require('./common/utils').escapeHtml;

////////////////////////////////////////////////////////////////////////////////

var default_rules = {};


default_rules.code_inline = function (tokens, idx, options, env, slf) {
  var token = tokens[idx];

  return  '<code' + slf.renderAttrs(token) + '>' +
          escapeHtml(tokens[idx].content) +
          '</code>';
};


default_rules.code_block = function (tokens, idx, options, env, slf) {
  var token = tokens[idx];

  return  '<pre' + slf.renderAttrs(token) + '><code>' +
          escapeHtml(tokens[idx].content) +
          '</code></pre>\n';
};


default_rules.fence = function (tokens, idx, options, env, slf) {
  var token = tokens[idx],
      info = token.info ? unescapeAll(token.info).trim() : '',
      langName = '',
      langAttrs = '',
      highlighted, i, arr, tmpAttrs, tmpToken;

  if (info) {
    arr = info.split(/(\s+)/g);
    langName = arr[0];
    langAttrs = arr.slice(1).join('');
  }

  if (options.highlight) {
    highlighted = options.highlight(token.content, langName, langAttrs) || escapeHtml(token.content);
  } else {
    highlighted = escapeHtml(token.content);
  }

  if (highlighted.indexOf('<pre') === 0) {
    return highlighted + '\n';
  }

  // If language exists, inject class like 'language-js'.
  // NOTE: Consider '/' delimiters escaped when writing regex patterns.
  if (info) {
    i = token.attrIndex('class');
    tmpAttrs = token.attrs ? token.attrs.slice() : [];

    if (i < 0) {
      tmpAttrs.push([ 'class', options.langPrefix + langName ]);
    } else {
      tmpAttrs[i] = tmpAttrs[i].slice();
      tmpAttrs[i][1] += ' ' + options.langPrefix + langName;
    }

    // Fake token just to render attributes
    tmpToken = {
      attrs: tmpAttrs
    };

    return  '<pre><code' + slf.renderAttrs(tmpToken) + '>'
          + highlighted
          + '</code></pre>\n';
  }


  return  '<pre><code' + slf.renderAttrs(token) + '>'
        + highlighted
        + '</code></pre>\n';
};


default_rules.image = function (tokens, idx, options, env, slf) {
  var token = tokens[idx];

  // "alt" contains user-generated text, should be escaped correctly.
  // However, title argument becomes "title" attribute on output HTML tag,
  // so we escape it here differently.
  var attrs = slf.renderAttrs(token);

  return '<img' + attrs + '>';
};


default_rules.hardbreak = function (tokens, idx, options /*, env */) {
  return options.xhtmlOut ? '<br />\n' : '<br>\n';
};
default_rules.softbreak = function (tokens, idx, options /*, env */) {
  return options.breaks ? (options.xhtmlOut ? '<br />\n' : '<br>\n') : '\n';
};


default_rules.text = function (tokens, idx /*, options, env */) {
  return escapeHtml(tokens[idx].content);
};


default_rules.html_block = function (tokens, idx /*, options, env */) {
  return tokens[idx].content;
};
default_rules.html_inline = function (tokens, idx /*, options, env */) {
  return tokens[idx].content;
};


/**
 * new Renderer()
 *
 * Creates new [[Renderer]] instance and fill [[Renderer#rules]] with defaults.
 **/
function Renderer() {

  /**
   * Renderer#rules -> Object
   *
   * Contains render rules for tokens. Can be updated and extended.
   *
   * Each rule is called as `rule(tokens, idx, options, env, renderer)`.
   *
   * The first argument is the array of tokens, the second is the index of the
   * current token being rendered. The others are the options object and the
   * environment object, passed from the call to [[MarkdownIt#render]]. The
   * last is a reference to the renderer instance, useful if you need to call
   * other rules from within the current one.
   *
   * See [[Renderer.render]] for an example of how to call the rules.
   **/
  this.rules = assign({}, default_rules);
}


/**
 * Renderer.renderAttrs(token) -> String
 *
 * Render token attributes to string.
 **/
Renderer.prototype.renderAttrs = function renderAttrs(token) {
  var i, l, result;

  if (!token.attrs) { return ''; }

  result = '';

  for (i = 0, l = token.attrs.length; i < l; i++) {
    result += ' ' + escapeHtml(token.attrs[i][0]) + '="' + escapeHtml(token.attrs[i][1]) + '"';
  }

  return result;
};


/**
 * Renderer.renderToken(tokens, idx, options) -> String
 * - tokens (Array): list of tokens
 * - idx (Number): token index to render
 * - options (Object): params of md.render()
 *
 * Default token renderer. Can be overridden by custom function
 * in [[Renderer#rules]].
 **/
Renderer.prototype.renderToken = function renderToken(tokens, idx, options) {
  var token = tokens[idx],
      rule;

  // Tight list paragraphs
  if (token.hidden) {
    return '';
  }

  // Run middleware
  if (token.middleware) {
    token.middleware(token, options);
  }

  rule = this.rules[token.type];

  // Replace token type with "paragraph" if this rule is not defined.
  if (typeof rule === 'undefined') {
    rule = this.rules.paragraph_open;
  }

  return rule(tokens, idx, options, {}, this);
};


/**
 * Renderer.renderInline(tokens, options, env) -> String
 * - tokens (Array): list on inline tokens
 * - options (Object): params of md.render()
 * - env (Object): additional data from parsed input
 *
 * The same as [[Renderer.render]], but for single token of `inline` type.
 **/
Renderer.prototype.renderInline = function (tokens, options, env) {
  var result = '',
      rules = this.rules,
      i, len;

  for (i = 0, len = tokens.length; i < len; i++) {
    if (typeof rules[tokens[i].type] !== 'undefined') {
      result += rules[tokens[i].type](tokens, i, options, env, this);
    } else {
      result += this.renderToken(tokens, i, options);
    }
  }

  return result;
};


/** internal
 * Renderer.renderInlineAsText(tokens, options, env) -> String
 * - tokens (Array): list on inline tokens
 * - options (Object): params of md.render()
 * - env (Object): additional data from parsed input
 *
 * Special kludge for image titles. Much faster than renderInline w/o plugins.
 **/
Renderer.prototype.renderInlineAsText = function (tokens, options, env) {
  var result = '',
      i, len;

  for (i = 0, len = tokens.length; i < len; i++) {
    if (tokens[i].type === 'text') {
      result += tokens[i].content;
    } else if (tokens[i].type === 'image') {
      result += this.renderInlineAsText(tokens[i].children, options, env);
    }
  }

  return result;
};


/**
 * Renderer.render(tokens, options, env) -> String
 * - tokens (Array): list on block tokens to render
 * - options (Object): params of md.render()
 * - env (Object): additional data from parsed input (references, for example)
 *
 * Takes token stream and generates HTML. Probably, you will never need to call
 * this method directly.
 **/
Renderer.prototype.render = function (tokens, options, env) {
  var i, len,
      result = '',
      rules = this.rules;

  for (i = 0, len = tokens.length; i < len; i++) {
    if (tokens[i].type === 'inline') {
      result += this.renderInline(tokens[i].children, options, env);
    } else if (typeof rules[tokens[i].type] !== 'undefined') {
      result += rules[tokens[i].type](tokens, i, options, env, this);
    } else {
      result += this.renderToken(tokens, i, options, env);
    }
  }

  return result;
};

module.exports = Renderer;
},{"./common/utils":1}],15:[function(require,module,exports){
// Token class

'use strict';


/**
 * class Token
 **/

/**
 * new Token(type, tag, nesting)
 *
 * Create new token and fill passed properties.
 **/
function Token(type, tag, nesting) {
  /**
   * Token#type -> String
   *
   * Type of the token (string, e.g. "paragraph_open").
   **/
  this.type = type;

  /**
   * Token#tag -> String
   *
   * HTML tag name, e.g. "p".
   **/
  this.tag = tag;

  /**
   * Token#attrs -> Array
   *
   * Html attributes. Format: `[ [ name1, value1 ], [ name2, value2 ] ]`.
   **/
  this.attrs = null;

  /**
   * Token#map -> Array
   *
   * Source map info. Format: `[ line_begin, line_end ]`.
   **/
  this.map = null;

  /**
   * Token#nesting -> Number
   *
   * Level change (number):
   *
   * -  `1` means the tag is opening
   * -  `0` means the tag is self-closing
   * - `-1` means the tag is closing
   **/
  this.nesting = nesting;

  /**
   * Token#level -> Number
   *
   * Nesting level, the same as `state.level`.
   **/
  this.level = 0;

  /**
   * Token#children -> Array
   *
   * An array of child nodes (inline and img tokens).
   **/
  this.children = null;

  /**
   * Token#content -> String
   *
   * In a case of self-closing tag (code, text, fence, etc.),
   * it has contents of this tag.
   **/
  this.content = '';

  /**
   * Token#markup -> String
   *
   * '*' or '_' for emphasis, fence string for fence, etc.
   **/
  this.markup = '';

  /**
   * Token#info -> String
   *
   * Additional information about parse (fence language, etc.).
   **/
  this.info = '';

  /**
   * Token#meta -> Object
   *
   * A place for plugins to store metadata.
   **/
  this.meta = null;

  /**
   * Token#block -> Boolean
   *
   * True for block-level tokens, false for inline tokens.
   * Used in renderer to calculate line breaks
   **/
  this.block = false;

  /**
   * Token#hidden -> Boolean
   *
   * If true, ignore this token when rendering. Used for tight lists
   * to hide paragraphs.
   **/
  this.hidden = false;
}


/**
 * Token.attrIndex(name) -> Number
 *
 * Search attribute index by name.
 **/
Token.prototype.attrIndex = function attrIndex(name) {
  var attrs, i, len;

  if (!this.attrs) { return -1; }

  attrs = this.attrs;

  for (i = 0, len = attrs.length; i < len; i++) {
    if (attrs[i][0] === name) {
      return i;
    }
  }
  return -1;
};


/**
 * Token.attrPush(attrData)
 *
 * Add `[ name, value ]` attribute to list. Init attrs if necessary.
 **/
Token.prototype.attrPush = function attrPush(attrData) {
  if (this.attrs) {
    this.attrs.push(attrData);
  } else {
    this.attrs = [ attrData ];
  }
};


/**
 * Token.attrSet(name, value)
 *
 * Set `name` attribute to `value`. Overwrite old value if exists.
 **/
Token.prototype.attrSet = function attrSet(name, value) {
  var idx = this.attrIndex(name),
      attrData = [ name, value ];

  if (idx < 0) {
    this.attrPush(attrData);
  } else {
    this.attrs[idx] = attrData;
  }
};


/**
 * Token.attrGet(name)
 *
 * Get attribute value by name.
 **/
Token.prototype.attrGet = function attrGet(name) {
  var idx = this.attrIndex(name),
      value = null;
  if (idx >= 0) {
    value = this.attrs[idx][1];
  }
  return value;
};


/**
 * Token.attrJoin(name, value)
 *
 * Join value to existing attribute via space. Or create new attribute if not
 * exists. Useful for classes.
 **/
Token.prototype.attrJoin = function attrJoin(name, value) {
  var idx = this.attrIndex(name);

  if (idx < 0) {
    this.attrPush([ name, value ]);
  } else {
    this.attrs[idx][1] = this.attrs[idx][1] + ' ' + value;
  }
};


module.exports = Token;
},{}]},{},[1])(1)
});
