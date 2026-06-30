(function() {
  'use strict';

  var state = {
    config: null,
    songs: [],
    selectedIndices: new Set(),
    failedIndices: new Set(),
    currentTaskId: null,
    logCollapsed: false,
    searching: false,
  };

  var $ = function(id) { return document.getElementById(id); };

  // ── Log ──

  function log(msg, level) {
    level = level || 'info';
    var el = $('logContent');
    var entry = document.createElement('div');
    entry.className = 'log-entry log-' + level;
    var time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    entry.textContent = '[' + time + '] ' + msg;
    el.appendChild(entry);
    el.scrollTop = el.scrollHeight;
    // Keep log buffer reasonable
    while (el.children.length > 500) {
      el.removeChild(el.firstChild);
    }
  }

  // ── Loading ──

  function showLoading(text) {
    $('loadingText').textContent = text || '加载中...';
    $('loadingOverlay').style.display = 'flex';
  }

  function hideLoading() {
    $('loadingOverlay').style.display = 'none';
  }

  // ── Progress ──

  function setProgress(current, total, songName) {
    var pct = total > 0 ? Math.round((current / total) * 100) : 0;
    $('progressBar').style.width = pct + '%';
    $('progressText').textContent = current + '/' + total;
    if (songName) {
      $('progressLabel').textContent = '下载中: ' + songName;
    }
  }

  function showDownloadPanel() {
    $('downloadPanel').style.display = 'block';
  }

  function hideDownloadPanel() {
    $('downloadPanel').style.display = 'none';
    $('progressBar').style.width = '0%';
    $('progressText').textContent = '0/0';
    $('progressLabel').textContent = '准备下载...';
  }

  // ── Sources ──

  function populateSources(sources) {
    var sel = $('sourceSelect');
    sel.innerHTML = '';
    sources.forEach(function(s) {
      var opt = document.createElement('option');
      opt.value = s.value;
      opt.textContent = s.label;
      sel.appendChild(opt);
    });
  }

  // ── Config ──

  function applyConfig(config) {
    state.config = config;
    if (config.source) $('sourceSelect').value = config.source;
    if (config.search_type) $('typeSelect').value = config.search_type;
    if (config.bitrate) $('bitrateSelect').value = config.bitrate;
    if (config.number) $('numberInput').value = config.number;
    if (config.output_dir) $('outputDirInput').value = config.output_dir;
    $('coverCheck').checked = config.download_cover !== false;
    $('lyricCheck').checked = config.download_lyric !== false;
  }

  function collectConfig() {
    return {
      source: $('sourceSelect').value,
      search_type: $('typeSelect').value,
      bitrate: $('bitrateSelect').value,
      number: parseInt($('numberInput').value) || 20,
      output_dir: $('outputDirInput').value,
      download_cover: $('coverCheck').checked,
      download_lyric: $('lyricCheck').checked,
    };
  }

  function saveCurrentConfig() {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.save_config(collectConfig());
    }
  }

  // ── Song List Rendering ──

  function renderSongs(songs) {
    state.songs = songs;
    state.selectedIndices = new Set();
    state.failedIndices = new Set();
    var list = $('resultList');
    list.innerHTML = '';

    if (!songs || songs.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">&#9835;</div><p>未找到结果</p></div>';
      $('resultCount').textContent = '';
      updateRetryFailedUI();
      return;
    }

    $('resultCount').textContent = '共 ' + songs.length + ' 首';

    var fragment = document.createDocumentFragment();

    songs.forEach(function(song, idx) {
      var item = document.createElement('div');
      item.className = 'song-item';
      item.dataset.index = idx;

      // Checkbox
      var check = document.createElement('input');
      check.type = 'checkbox';
      check.className = 'song-check';
      check.setAttribute('aria-label', '选择 ' + (song.name || '未知'));
      check.addEventListener('change', function(e) {
        e.stopPropagation();
        if (e.target.checked) {
          state.selectedIndices.add(idx);
          item.classList.add('selected');
        } else {
          state.selectedIndices.delete(idx);
          item.classList.remove('selected');
        }
        updateSelectionUI();
      });

      // Cover
      var cover = document.createElement('div');
      cover.className = 'song-cover';
      if (song.cover && song.cover.length > 10) {
        var img = document.createElement('img');
        img.src = song.cover;
        img.alt = song.name || '';
        img.loading = 'lazy';
        img.onerror = function() { this.parentElement.textContent = '\u266B'; };
        cover.appendChild(img);
      } else {
        cover.textContent = '\u266B';
      }

      // Info
      var info = document.createElement('div');
      info.className = 'song-info';

      var nameEl = document.createElement('div');
      nameEl.className = 'song-name';
      nameEl.textContent = song.name || '未知';

      if (song.source) {
        var tag = document.createElement('span');
        tag.className = 'source-tag';
        tag.textContent = song.source;
        nameEl.appendChild(tag);
      }

      if (song.bitrate === 'flac' || song.bitrate === '999') {
        var hires = document.createElement('span');
        hires.className = 'hires-tag';
        hires.textContent = 'Hi-Res';
        nameEl.appendChild(hires);
      }

      var meta = document.createElement('div');
      meta.className = 'song-meta';
      var metaParts = [
        song.artist || '未知',
        song.album ? (' \xB7 ' + song.album) : '',
        song.duration ? (' \xB7 ' + song.duration) : ''
      ];
      meta.textContent = metaParts.join('');

      info.appendChild(nameEl);
      info.appendChild(meta);

      // Duration
      var dur = document.createElement('div');
      dur.className = 'song-duration';
      dur.textContent = song.duration || '';

      // Status
      var status = document.createElement('div');
      status.className = 'song-status';
      status.id = 'song-status-' + idx;

      item.appendChild(check);
      item.appendChild(cover);
      item.appendChild(info);
      item.appendChild(dur);
      item.appendChild(status);

      item.addEventListener('click', function(e) {
        if (e.target === check) return;
        check.checked = !check.checked;
        check.dispatchEvent(new Event('change'));
      });

      fragment.appendChild(item);
    });

    list.appendChild(fragment);
    updateSelectionUI();
    updateRetryFailedUI();
  }

  function updateSelectionUI() {
    var count = state.selectedIndices.size;
    var btn = $('downloadSelectedBtn');
    if (count > 0) {
      btn.textContent = '下载选中 (' + count + ')';
      btn.disabled = false;
    } else {
      btn.textContent = '下载选中';
      btn.disabled = false;
    }
  }

  function updateRetryFailedUI() {
    var btn = $('retryFailedBtn');
    if (!btn) return;
    var count = state.failedIndices.size;
    btn.disabled = count === 0;
    btn.textContent = count > 0 ? ('重试失败 (' + count + ')') : '重试失败';
  }

  function setSongStatus(idx, icon, cls) {
    var el = $('song-status-' + idx);
    if (el) {
      el.textContent = icon;
      el.className = 'song-status ' + (cls || '');
    }
  }

  // ── Init ──

  async function init() {
    log('应用启动中...', 'info');

    if (!window.pywebview) {
      log('pywebview 未就绪，请在桌面窗口中运行', 'error');
      return;
    }

    try {
      var opts = await window.pywebview.api.get_valid_options();
      populateSources(opts.sources);

      var config = await window.pywebview.api.get_config();
      applyConfig(config);

      log('初始化完成，正在启动浏览器...', 'info');
      showLoading('正在启动浏览器并通过 Cloudflare 验证...');

      var result = await window.pywebview.api.init_browser();
      hideLoading();

      if (result.ready) {
        log('浏览器就绪，可以开始搜索', 'success');
      } else {
        log('浏览器初始化失败，请检查 Chrome 是否安装', 'error');
      }
    } catch (err) {
      hideLoading();
      log('初始化失败: ' + err, 'error');
    }

    bindEvents();
    $('searchInput').focus();
  }

  // ── Events ──

  function bindEvents() {
    $('searchBtn').addEventListener('click', doSearch);
    $('searchInput').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') doSearch();
    });

    $('downloadSelectedBtn').addEventListener('click', doDownloadSelected);
    $('retryFailedBtn').addEventListener('click', retryFailed);
    $('selectAllBtn').addEventListener('click', selectAll);
    $('deselectAllBtn').addEventListener('click', deselectAll);
    $('cancelDownloadBtn').addEventListener('click', cancelDownload);

    $('browseDirBtn').addEventListener('click', async function() {
      try {
        var path = await window.pywebview.api.select_directory();
        if (path) {
          $('outputDirInput').value = path;
          saveCurrentConfig();
        }
      } catch (err) {
        log('选择目录失败: ' + err, 'error');
      }
    });

    $('openDirBtn').addEventListener('click', function() {
      window.pywebview.api.open_download_dir($('outputDirInput').value);
    });

    $('envCheckBtn').addEventListener('click', showEnvCheck);
    $('closeEnvModal').addEventListener('click', function() {
      $('envModal').style.display = 'none';
    });

    // Click outside modal to close
    $('envModal').addEventListener('click', function(e) {
      if (e.target === this) this.style.display = 'none';
    });

    $('toggleLogBtn').addEventListener('click', function() {
      state.logCollapsed = !state.logCollapsed;
      var panel = document.querySelector('.log-panel');
      panel.classList.toggle('collapsed', state.logCollapsed);
      $('toggleLogBtn').textContent = state.logCollapsed ? '展开' : '折叠';
    });

    // Auto-save on setting changes
    var autoSaveIds = ['sourceSelect', 'typeSelect', 'bitrateSelect', 'numberInput', 'coverCheck', 'lyricCheck'];
    autoSaveIds.forEach(function(id) {
      $(id).addEventListener('change', saveCurrentConfig);
    });

    // Python event listeners
    window.addEventListener('py-log', function(e) {
      log(e.detail.message, e.detail.level);
    });

    window.addEventListener('py-progress', function(e) {
      var d = e.detail;
      if (d.type === 'start') {
        showDownloadPanel();
        setProgress(0, d.total, '');
      } else if (d.type === 'progress') {
        setProgress(d.current, d.total, d.song_name);
        setSongStatus(d.current, '\u2B07', 'status-downloading');
      } else if (d.type === 'song_done') {
        var icon = d.result === 'success' ? '\u2713' : (d.result === 'skip' ? '\u2013' : '\u2717');
        var cls = d.result === 'success' ? 'status-done' : (d.result === 'skip' ? 'status-skip' : 'status-fail');
        setSongStatus(d.index, icon, cls);
        if (d.result === 'fail') {
          state.failedIndices.add(d.index);
        } else {
          state.failedIndices.delete(d.index);
        }
        updateRetryFailedUI();
        setProgress(d.current, d.total, '');
      } else if (d.type === 'complete') {
        var total = d.success + d.fail + d.skip;
        setProgress(total, total, '');
        if (d.success === total) {
          log('全部下载完成', 'success');
        } else if (d.fail > 0) {
          log('下载完成，' + d.fail + ' 首失败', 'warn');
        }
        setTimeout(function() { hideDownloadPanel(); }, 2000);
        state.currentTaskId = null;
      }
    });
  }

  // ── Search ──

  async function doSearch() {
    var keyword = $('searchInput').value.trim();
    if (!keyword) {
      log('请输入搜索关键词', 'warn');
      $('searchInput').focus();
      return;
    }
    if (state.searching) return;
    state.searching = true;

    saveCurrentConfig();
    showLoading('正在搜索...');
    $('searchBtn').disabled = true;

    try {
      var source = $('sourceSelect').value;
      var type = $('typeSelect').value;
      var number = parseInt($('numberInput').value) || 20;
      var songs = await window.pywebview.api.search(keyword, source, type, number);
      renderSongs(songs);
    } catch (err) {
      log('搜索失败: ' + err, 'error');
    } finally {
      hideLoading();
      $('searchBtn').disabled = false;
      state.searching = false;
    }
  }

  // ── Selection ──

  function selectAll() {
    state.songs.forEach(function(_, idx) {
      state.selectedIndices.add(idx);
    });
    document.querySelectorAll('.song-item').forEach(function(el) {
      el.classList.add('selected');
      var cb = el.querySelector('.song-check');
      if (cb) cb.checked = true;
    });
    updateSelectionUI();
  }

  function deselectAll() {
    state.selectedIndices.clear();
    document.querySelectorAll('.song-item').forEach(function(el) {
      el.classList.remove('selected');
      var cb = el.querySelector('.song-check');
      if (cb) cb.checked = false;
    });
    updateSelectionUI();
  }

  // ── Download ──

  async function doDownloadSelected() {
    if (state.selectedIndices.size === 0) {
      log('请先选择要下载的歌曲', 'warn');
      return;
    }
    var indicesArr = Array.from(state.selectedIndices);
    var selectedSongs = indicesArr.map(function(i) {
      var song = Object.assign({}, state.songs[i]);
      song._gui_index = i;
      return song;
    });
    var config = collectConfig();
    log('开始下载 ' + selectedSongs.length + ' 首歌曲...', 'info');
    try {
      var taskId = await window.pywebview.api.start_download(
        selectedSongs,
        config.source,
        config.bitrate,
        config.download_lyric,
        config.download_cover,
        config.output_dir
      );
      state.currentTaskId = taskId;
      indicesArr.forEach(function(idx) {
        setSongStatus(idx, '\u231B', '');
      });
    } catch (err) {
      log('下载启动失败: ' + err, 'error');
    }
  }

  async function retryFailed() {
    if (state.failedIndices.size === 0) return;
    state.selectedIndices = new Set(state.failedIndices);
    await doDownloadSelected();
  }

  function cancelDownload() {
    if (state.currentTaskId) {
      window.pywebview.api.cancel_download(state.currentTaskId);
      log('正在取消下载...', 'warn');
    }
  }

  // ── Environment Check ──

  async function showEnvCheck() {
    showLoading('检查环境...');
    try {
      var results = await window.pywebview.api.check_environment();
      var body = $('envModalBody');
      body.innerHTML = '';
      results.forEach(function(r) {
        var item = document.createElement('div');
        item.className = 'env-item';
        item.innerHTML =
          '<div><div style="font-weight:600">' + r.name + '</div>' +
          '<div class="env-detail">' + r.detail + '</div></div>' +
          '<span class="' + (r.ok ? 'env-status-ok' : 'env-status-fail') + '">' +
          (r.ok ? '\u2713 通过' : '\u2717 失败') + '</span>';
        body.appendChild(item);
      });
      $('envModal').style.display = 'flex';
    } catch (err) {
      log('环境检查失败: ' + err, 'error');
    } finally {
      hideLoading();
    }
  }

  // ── Boot ──

  window.addEventListener('pywebviewready', init);
})();
