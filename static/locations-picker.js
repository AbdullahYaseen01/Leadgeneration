/**
 * Location picker: state/region → city → postal codes (or legacy region → flat cities).
 * Container: [data-pills], [data-search], [data-tree], [data-dropdown], [data-toggle-dropdown], [data-unselect].
 */
(function (global) {
  var SEP = "\x1e";

  function isLegacyRegionMap(regionMap) {
    if (!regionMap || typeof regionMap !== "object") return false;
    var keys = Object.keys(regionMap);
    if (!keys.length) return false;
    return Array.isArray(regionMap[keys[0]]);
  }

  function LocationPicker(root, regionMap, options) {
    if (!root || !regionMap) return null;
    options = options || {};

    if (isLegacyRegionMap(regionMap)) {
      return legacyPicker(root, regionMap, options);
    }
    return nestedPicker(root, regionMap, options);
  }

  function keyNested(state, city, plz) {
    return state + SEP + city + SEP + (plz || "");
  }

  function nestedPicker(root, stateMap, options) {
    var selected = new Set();
    var searchQ = "";
    var expandedStates = new Set(Object.keys(stateMap));
    var expandedCities = new Set();

    Object.keys(stateMap).forEach(function (state) {
      var cities = stateMap[state] || {};
      Object.keys(cities).forEach(function (city) {
        var plzs = cities[city] || [];
        if (plzs.length <= 40) expandedCities.add(state + SEP + city);
      });
    });

    var pillsEl = root.querySelector("[data-pills]");
    var searchEl = root.querySelector("[data-search]");
    var treeEl = root.querySelector("[data-tree]");
    var dd = root.querySelector("[data-dropdown]");
    var btnOpen = root.querySelector("[data-toggle-dropdown]");
    var unsel = root.querySelector("[data-unselect]");

    function postalsFor(state, city) {
      var arr = (stateMap[state] && stateMap[state][city]) || [];
      return Array.isArray(arr) ? arr : [];
    }

    function totalPostalsInState(state) {
      var n = 0;
      Object.keys(stateMap[state] || {}).forEach(function (city) {
        var p = postalsFor(state, city);
        n += p.length > 0 ? p.length : 1;
      });
      return n;
    }

    function countSelectedInState(state) {
      var n = 0;
      Object.keys(stateMap[state] || {}).forEach(function (city) {
        var plzs = postalsFor(state, city);
        if (plzs.length === 0) {
          if (selected.has(keyNested(state, city, ""))) n += 1;
        } else {
          plzs.forEach(function (p) {
            if (selected.has(keyNested(state, city, p))) n += 1;
          });
        }
      });
      return n;
    }

    function stateFullySelected(state) {
      var tot = totalPostalsInState(state);
      return tot > 0 && countSelectedInState(state) === tot;
    }

    function statePartiallySelected(state) {
      var c = countSelectedInState(state);
      return c > 0 && c < totalPostalsInState(state);
    }

    function cityFullySelected(state, city) {
      var plzs = postalsFor(state, city);
      if (plzs.length === 0) return selected.has(keyNested(state, city, ""));
      return plzs.every(function (p) {
        return selected.has(keyNested(state, city, p));
      });
    }

    function cityPartiallySelected(state, city) {
      var plzs = postalsFor(state, city);
      if (plzs.length === 0) return false;
      var n = plzs.filter(function (p) {
        return selected.has(keyNested(state, city, p));
      }).length;
      return n > 0 && n < plzs.length;
    }

    function setStateAll(state, on) {
      Object.keys(stateMap[state] || {}).forEach(function (city) {
        setCityAll(state, city, on);
      });
    }

    function setCityAll(state, city, on) {
      var plzs = postalsFor(state, city);
      if (plzs.length === 0) {
        if (on) selected.add(keyNested(state, city, ""));
        else selected.delete(keyNested(state, city, ""));
        return;
      }
      plzs.forEach(function (p) {
        if (on) selected.add(keyNested(state, city, p));
        else selected.delete(keyNested(state, city, p));
      });
    }

    function togglePostal(state, city, plz, on) {
      var k = keyNested(state, city, plz);
      if (on) selected.add(k);
      else selected.delete(k);
    }

    function qLower() {
      return (searchQ || "").trim().toLowerCase();
    }

    function stateMatches(state) {
      var q = qLower();
      if (!q) return true;
      if (state.toLowerCase().indexOf(q) !== -1) return true;
      var cities = stateMap[state] || {};
      return Object.keys(cities).some(function (city) {
        if (city.toLowerCase().indexOf(q) !== -1) return true;
        return (cities[city] || []).some(function (p) {
          return String(p).indexOf(q) !== -1;
        });
      });
    }

    function cityMatches(state, city) {
      var q = qLower();
      if (!q) return true;
      if (state.toLowerCase().indexOf(q) !== -1) return true;
      if (city.toLowerCase().indexOf(q) !== -1) return true;
      return postalsFor(state, city).some(function (p) {
        return String(p).indexOf(q) !== -1;
      });
    }

    function plzMatches(state, city, plz) {
      var q = qLower();
      if (!q) return true;
      if (state.toLowerCase().indexOf(q) !== -1) return true;
      if (city.toLowerCase().indexOf(q) !== -1) return true;
      return String(plz).indexOf(q) !== -1;
    }

    function getSelectedStrings() {
      var out = [];
      Object.keys(stateMap)
        .sort()
        .forEach(function (state) {
          Object.keys(stateMap[state] || {})
            .sort()
            .forEach(function (city) {
              var plzs = postalsFor(state, city);
              if (plzs.length === 0) {
                if (selected.has(keyNested(state, city, ""))) out.push(city);
                return;
              }
              var picked = plzs.filter(function (p) {
                return selected.has(keyNested(state, city, p));
              });
              if (!picked.length) return;
              if (picked.length === plzs.length) out.push(city);
              else
                picked.forEach(function (p) {
                  out.push(p + " " + city);
                });
            });
        });
      return out;
    }

    function getPillItems() {
      var items = [];
      Object.keys(stateMap).forEach(function (state) {
        Object.keys(stateMap[state] || {}).forEach(function (city) {
          var plzs = postalsFor(state, city);
          if (plzs.length === 0) {
            if (selected.has(keyNested(state, city, "")))
              items.push({
                label: city,
                keys: [keyNested(state, city, "")],
              });
            return;
          }
          var picked = plzs.filter(function (p) {
            return selected.has(keyNested(state, city, p));
          });
          if (!picked.length) return;
          if (picked.length === plzs.length) {
            items.push({
              label: city,
              keys: plzs.map(function (p) {
                return keyNested(state, city, p);
              }),
            });
          } else {
            picked.forEach(function (p) {
              items.push({
                label: p + " postal code",
                keys: [keyNested(state, city, p)],
              });
            });
          }
        });
      });
      items.sort(function (a, b) {
        return a.label.localeCompare(b.label);
      });
      return items;
    }

    function renderPills() {
      if (!pillsEl) return;
      pillsEl.innerHTML = "";
      var items = getPillItems();
      var maxShow = 8;
      items.slice(0, maxShow).forEach(function (item) {
        var span = document.createElement("span");
        span.className = "loc-pill";
        span.appendChild(document.createTextNode(item.label + " "));
        var x = document.createElement("button");
        x.type = "button";
        x.className = "loc-pill-x";
        x.setAttribute("aria-label", "Remove");
        x.textContent = "×";
        x.addEventListener("click", function () {
          item.keys.forEach(function (k) {
            selected.delete(k);
          });
          render();
        });
        span.appendChild(x);
        pillsEl.appendChild(span);
      });
      if (items.length > maxShow) {
        var more = document.createElement("span");
        more.className = "loc-pill loc-pill-more";
        more.textContent = "+ " + (items.length - maxShow) + " …";
        pillsEl.appendChild(more);
      }
    }

    function renderPlzRows(state, city, container) {
      var plzs = postalsFor(state, city);
      var sc = state + SEP + city;
      if (!expandedCities.has(sc)) return;
      var wrap = document.createElement("div");
      wrap.className = "loc-plz-block";
      plzs.forEach(function (plz) {
        if (!plzMatches(state, city, plz)) return;
        var row = document.createElement("label");
        row.className = "loc-plz-row";
        var ccb = document.createElement("input");
        ccb.type = "checkbox";
        ccb.checked = selected.has(keyNested(state, city, plz));
        ccb.addEventListener("change", function () {
          togglePostal(state, city, plz, ccb.checked);
          render();
        });
        row.appendChild(ccb);
        var lab = document.createElement("span");
        lab.className = "loc-plz-label";
        lab.textContent = plz + " postal code";
        row.appendChild(lab);
        wrap.appendChild(row);
      });
      container.appendChild(wrap);
    }

    function renderTree() {
      if (!treeEl) return;
      treeEl.innerHTML = "";
      Object.keys(stateMap)
        .sort()
        .forEach(function (state) {
          if (!stateMatches(state)) return;

          var wrap = document.createElement("div");
          wrap.className = "loc-tree-state";

          var head = document.createElement("div");
          head.className = "loc-region-head loc-tree-row";

          var exp = document.createElement("button");
          exp.type = "button";
          exp.className = "loc-exp";
          exp.setAttribute("aria-label", "Expand or collapse");
          exp.textContent = expandedStates.has(state) ? "−" : "+";
          exp.addEventListener("click", function () {
            if (expandedStates.has(state)) expandedStates.delete(state);
            else expandedStates.add(state);
            renderTree();
          });

          var cb = document.createElement("input");
          cb.type = "checkbox";
          cb.checked = stateFullySelected(state);
          cb.indeterminate = statePartiallySelected(state);
          cb.addEventListener("change", function () {
            setStateAll(state, cb.checked);
            render();
          });

          var lab = document.createElement("span");
          lab.className = "loc-region-label";
          lab.textContent = state;

          head.appendChild(exp);
          head.appendChild(cb);
          head.appendChild(lab);
          wrap.appendChild(head);

          if (expandedStates.has(state)) {
            var cityCol = document.createElement("div");
            cityCol.className = "loc-city-tree";

            Object.keys(stateMap[state] || {})
              .sort()
              .forEach(function (city) {
                if (!cityMatches(state, city)) return;
                var plzs = postalsFor(state, city);
                var sc = state + SEP + city;
                var cityWrap = document.createElement("div");
                cityWrap.className = "loc-city-node";

                var crow = document.createElement("div");
                crow.className = "loc-city-head loc-tree-row";

                if (plzs.length > 0) {
                  var cexp = document.createElement("button");
                  cexp.type = "button";
                  cexp.className = "loc-exp";
                  cexp.setAttribute("aria-label", "Expand or collapse postal codes");
                  cexp.textContent = expandedCities.has(sc) ? "−" : "+";
                  cexp.addEventListener("click", function () {
                    if (expandedCities.has(sc)) expandedCities.delete(sc);
                    else expandedCities.add(sc);
                    renderTree();
                  });
                  crow.appendChild(cexp);
                } else {
                  var ph = document.createElement("span");
                  ph.className = "loc-exp loc-exp-spacer";
                  crow.appendChild(ph);
                }

                var ccb = document.createElement("input");
                ccb.type = "checkbox";
                ccb.checked = cityFullySelected(state, city);
                ccb.indeterminate = cityPartiallySelected(state, city);
                ccb.addEventListener("change", function () {
                  setCityAll(state, city, ccb.checked);
                  render();
                });
                crow.appendChild(ccb);

                var clab = document.createElement("span");
                clab.className = "loc-city-name";
                clab.textContent = city;
                crow.appendChild(clab);

                cityWrap.appendChild(crow);

                if (plzs.length > 0) renderPlzRows(state, city, cityWrap);
                cityCol.appendChild(cityWrap);
              });

            wrap.appendChild(cityCol);
          }

          treeEl.appendChild(wrap);
        });
    }

    function render() {
      renderPills();
      renderTree();
    }

    var dropdownOpen = false;

    function setDropdownOpen(open) {
      if (!dd || !btnOpen) return;
      dropdownOpen = !!open;
      dd.hidden = !dropdownOpen;
      btnOpen.setAttribute("aria-expanded", dropdownOpen ? "true" : "false");
    }

    if (searchEl) {
      searchEl.addEventListener("input", function () {
        searchQ = searchEl.value || "";
        renderTree();
        setDropdownOpen(true);
      });
      searchEl.addEventListener("focus", function () {
        if ((searchEl.value || "").trim()) setDropdownOpen(true);
      });
    }

    if (unsel) {
      unsel.addEventListener("click", function (e) {
        e.preventDefault();
        selected.clear();
        render();
      });
    }

    if (btnOpen && dd) {
      btnOpen.addEventListener("click", function () {
        setDropdownOpen(!dropdownOpen);
      });
    }

    render();

    return {
      getSelected: function () {
        return getSelectedStrings();
      },
      selectCities: function (arr) {
        if (!arr || !arr.length) return;
        arr.forEach(function (token) {
          var t = String(token).trim();
          if (!t) return;
          Object.keys(stateMap).some(function (state) {
            return Object.keys(stateMap[state] || {}).some(function (city) {
              if (city.toLowerCase() === t.toLowerCase()) {
                setCityAll(state, city, true);
                return true;
              }
              var plzs = postalsFor(state, city);
              var m = t.match(/^(\d{4,5})\s+(.+)$/i);
              if (m && m[2].toLowerCase() === city.toLowerCase() && plzs.indexOf(m[1]) !== -1) {
                selected.add(keyNested(state, city, m[1]));
                return true;
              }
              return false;
            });
          });
        });
        render();
      },
      clear: function () {
        selected.clear();
        render();
      },
      setDisabled: function (d) {
        root.style.pointerEvents = d ? "none" : "";
        root.style.opacity = d ? "0.55" : "";
        root.querySelectorAll("input,button,select,textarea").forEach(function (el) {
          el.disabled = !!d;
        });
      },
    };
  }

  function legacyPicker(root, regionMap, options) {
    var selected = new Set();
    var expanded = new Set(Object.keys(regionMap));
    var searchQ = "";

    var pillsEl = root.querySelector("[data-pills]");
    var searchEl = root.querySelector("[data-search]");
    var treeEl = root.querySelector("[data-tree]");
    var dd = root.querySelector("[data-dropdown]");
    var btnOpen = root.querySelector("[data-toggle-dropdown]");
    var unsel = root.querySelector("[data-unselect]");

    function citiesInRegion(region) {
      return regionMap[region] || [];
    }

    function regionFullySelected(region) {
      var cities = citiesInRegion(region);
      if (cities.length === 0) return false;
      return cities.every(function (c) {
        return selected.has(c);
      });
    }

    function regionPartiallySelected(region) {
      var cities = citiesInRegion(region);
      var n = cities.filter(function (c) {
        return selected.has(c);
      }).length;
      return n > 0 && n < cities.length;
    }

    function toggleRegion(region, on) {
      citiesInRegion(region).forEach(function (c) {
        if (on) selected.add(c);
        else selected.delete(c);
      });
      render();
    }

    function toggleCity(city, on) {
      if (on) selected.add(city);
      else selected.delete(city);
      render();
    }

    function renderPills() {
      if (!pillsEl) return;
      pillsEl.innerHTML = "";
      var arr = Array.from(selected).sort();
      var maxShow = 8;
      arr.slice(0, maxShow).forEach(function (city) {
        var span = document.createElement("span");
        span.className = "loc-pill";
        span.appendChild(document.createTextNode(city + " "));
        var x = document.createElement("button");
        x.type = "button";
        x.className = "loc-pill-x";
        x.setAttribute("aria-label", "Remove");
        x.textContent = "×";
        x.addEventListener("click", function () {
          selected.delete(city);
          render();
        });
        span.appendChild(x);
        pillsEl.appendChild(span);
      });
      if (arr.length > maxShow) {
        var more = document.createElement("span");
        more.className = "loc-pill loc-pill-more";
        more.textContent = "+ " + (arr.length - maxShow) + " …";
        pillsEl.appendChild(more);
      }
    }

    function qLower() {
      return searchQ.trim().toLowerCase();
    }

    function regionMatches(region) {
      var q = qLower();
      if (!q) return true;
      if (region.toLowerCase().indexOf(q) !== -1) return true;
      return citiesInRegion(region).some(function (c) {
        return c.toLowerCase().indexOf(q) !== -1;
      });
    }

    function cityMatches(region, city) {
      var q = qLower();
      if (!q) return true;
      if (region.toLowerCase().indexOf(q) !== -1) return true;
      return city.toLowerCase().indexOf(q) !== -1;
    }

    function renderCityRows(region, container) {
      citiesInRegion(region).forEach(function (city) {
        if (!cityMatches(region, city)) return;
        var row = document.createElement("label");
        row.className = "loc-city-row";
        var ccb = document.createElement("input");
        ccb.type = "checkbox";
        ccb.checked = selected.has(city);
        ccb.addEventListener("change", function () {
          toggleCity(city, ccb.checked);
        });
        row.appendChild(ccb);
        row.appendChild(document.createTextNode(" " + city));
        container.appendChild(row);
      });
    }

    function renderTree() {
      if (!treeEl) return;
      treeEl.innerHTML = "";
      var regionKeys = Object.keys(regionMap).sort();

      if (regionKeys.length === 1) {
        var region = regionKeys[0];
        if (!regionMatches(region)) return;

        var toolbar = document.createElement("div");
        toolbar.className = "loc-region-head loc-flat-toolbar";
        var cbAll = document.createElement("input");
        cbAll.type = "checkbox";
        cbAll.checked = regionFullySelected(region);
        cbAll.indeterminate = regionPartiallySelected(region);
        cbAll.addEventListener("change", function () {
          toggleRegion(region, cbAll.checked);
        });
        var labAll = document.createElement("span");
        labAll.className = "loc-region-label";
        labAll.textContent = "Select all";
        toolbar.appendChild(cbAll);
        toolbar.appendChild(labAll);
        treeEl.appendChild(toolbar);

        var childW = document.createElement("div");
        childW.className = "loc-city-list loc-city-list-flat";
        renderCityRows(region, childW);
        treeEl.appendChild(childW);
        return;
      }

      regionKeys.forEach(function (region) {
        if (!regionMatches(region)) return;

        var wrap = document.createElement("div");
        wrap.className = "loc-region";

        var head = document.createElement("div");
        head.className = "loc-region-head";

        var exp = document.createElement("button");
        exp.type = "button";
        exp.className = "loc-exp";
        exp.setAttribute("aria-label", "Expand or collapse cities");
        exp.textContent = expanded.has(region) ? "−" : "+";
        exp.addEventListener("click", function () {
          if (expanded.has(region)) expanded.delete(region);
          else expanded.add(region);
          renderTree();
        });

        var cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = regionFullySelected(region);
        cb.indeterminate = regionPartiallySelected(region);
        cb.addEventListener("change", function () {
          toggleRegion(region, cb.checked);
        });

        var lab = document.createElement("span");
        lab.className = "loc-region-label";
        lab.textContent = region;

        head.appendChild(exp);
        head.appendChild(cb);
        head.appendChild(lab);
        wrap.appendChild(head);

        if (expanded.has(region)) {
          var childW = document.createElement("div");
          childW.className = "loc-city-list";
          renderCityRows(region, childW);
          wrap.appendChild(childW);
        }

        treeEl.appendChild(wrap);
      });
    }

    function render() {
      renderPills();
      renderTree();
    }

    var dropdownOpen = false;

    function setDropdownOpen(open) {
      if (!dd || !btnOpen) return;
      dropdownOpen = !!open;
      dd.hidden = !dropdownOpen;
      btnOpen.setAttribute("aria-expanded", dropdownOpen ? "true" : "false");
    }

    if (searchEl) {
      searchEl.addEventListener("input", function () {
        searchQ = searchEl.value || "";
        renderTree();
        setDropdownOpen(true);
      });
      searchEl.addEventListener("focus", function () {
        if ((searchEl.value || "").trim()) setDropdownOpen(true);
      });
    }

    if (unsel) {
      unsel.addEventListener("click", function (e) {
        e.preventDefault();
        selected.clear();
        render();
      });
    }

    if (btnOpen && dd) {
      btnOpen.addEventListener("click", function () {
        setDropdownOpen(!dropdownOpen);
      });
    }

    render();

    return {
      getSelected: function () {
        return Array.from(selected);
      },
      selectCities: function (arr) {
        if (!arr || !arr.length) return;
        arr.forEach(function (city) {
          Object.keys(regionMap).forEach(function (region) {
            if (citiesInRegion(region).indexOf(city) !== -1) selected.add(city);
          });
        });
        render();
      },
      clear: function () {
        selected.clear();
        render();
      },
      setDisabled: function (d) {
        root.style.pointerEvents = d ? "none" : "";
        root.style.opacity = d ? "0.55" : "";
        root.querySelectorAll("input,button,select,textarea").forEach(function (el) {
          el.disabled = !!d;
        });
      },
    };
  }

  global.LocationPicker = LocationPicker;
})(typeof window !== "undefined" ? window : this);
