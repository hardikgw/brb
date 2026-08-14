// Viewer-request CloudFront Function for the site distribution.
//
// 1) 301 apex -> www so every hostname collapses onto the canonical host
//    (all canonicals, JSON-LD, and the sitemap declare www).
// 2) 301 /path/ -> /path so trailing-slash URLs stop returning the S3
//    origin's raw 403 (only bare alias keys exist in the bucket).
//
// The distribution is NOT managed by this stack: attach this function to the
// default behavior as its viewer-request function once (console or CLI);
// the association survives later function updates deployed from here.

function handler(event) {
  var request = event.request;
  var host = request.headers.host ? request.headers.host.value : '';
  var uri = request.uri;

  if (host === 'backroombrewery.com') {
    return redirect('https://www.backroombrewery.com' + trimSlash(uri) + search(request));
  }

  if (uri.length > 1 && uri.endsWith('/')) {
    return redirect('https://' + host + trimSlash(uri) + search(request));
  }

  return request;
}

function trimSlash(uri) {
  return uri.length > 1 && uri.endsWith('/') ? uri.slice(0, -1) : uri;
}

function search(request) {
  var parts = [];
  for (var key in request.querystring) {
    var entry = request.querystring[key];
    if (entry.multiValue) {
      for (var i = 0; i < entry.multiValue.length; i++) {
        parts.push(key + '=' + entry.multiValue[i].value);
      }
    } else if (entry.value === '') {
      parts.push(key);
    } else {
      parts.push(key + '=' + entry.value);
    }
  }
  return parts.length ? '?' + parts.join('&') : '';
}

function redirect(location) {
  return {
    statusCode: 301,
    statusDescription: 'Moved Permanently',
    headers: { location: { value: location } }
  };
}
