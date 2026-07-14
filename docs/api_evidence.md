# iStore Solar API Evidence

This report summarizes three private browser HAR captures from `home.istore.net.au`.
The source HAR files remain under `private/`, which is ignored by Git. This
document intentionally contains no real credentials, cookies, tokens, email
addresses, addresses, site IDs, serial numbers, device IDs, account identifiers,
or opaque private values.

All opaque path segments and identifiers are replaced with placeholders such as
`<APP_ID>`, `<UNKNOWN_SID_PARAM>`, `<SITE_ID>`, `<DEVICE_ID>`, `<ORG_ID>`,
`<USER_ID>`, `<ACCESS_TOKEN>`, `<EMAIL>`, and `<SERIAL_NUMBER>`.

## Capture Summary

- Capture 1: active logged-in portal session; no login request observed.
- Capture 2: includes logout, login, post-login bootstrap, discovery, and live
  portal polling.
- Capture 3: preserved-log capture from login through dashboard load, live
  polling, daily/monthly energy chart navigation, grid import/export history,
  and separate human operating-state notes.
- Host observed: `home.istore.net.au`.
- Transport: HTTPS browser API calls.
- Most API responses use HTTP `200` with an application-level `code` plus
  either `message` or `msg`.
- Several browser requests have HAR status `0`; these appear to be cancelled or
  incomplete browser requests, not useful API responses.

## Authentication And Session Flow

Observed login endpoint:

```text
POST /hossain-bff/framework/v1.0/user/login
```

Observed login request body keys:

```json
{
  "strategy": "<STRING>",
  "account": "<EMAIL_OR_ACCOUNT>",
  "password": "<ENCRYPTED_OR_TRANSFORMED_PASSWORD>"
}
```

The working browser request shows the `password` field as a long base64-like
string, not a normal plaintext-shaped value. The real value is private and is
not recorded here.

Observed successful login response:

- HTTP status: `200`
- Response body: empty in the capture
- No `Location` header observed
- No `Set-Cookie` values observed in the HAR parser output
- No response cookies observed

After login, the browser sends a bootstrap sequence. The first request after
login did not use `_sid_`. In the newest preserved-log capture, the next
request did.

Sanitized sequence immediately after the captured login:

1. `POST /hossain-bff/framework/v1.0/user/<USER_ID>`
   - Query keys: none
   - Uses `<UNKNOWN_SID_PARAM>`: no
2. `POST /app-portal/web/v1/user/app/asset/tree?_sid_=<UNKNOWN_SID_PARAM>&appId=<APP_ID>&needAssociateAsset=<BOOL>&resourceTypes=<STRING>`
   - First post-login request observed with `_sid_` in capture 3.
3. `POST /app-portal/web/v1/lion/get?_sid_=<UNKNOWN_SID_PARAM>`
4. `POST /app-portal/web/v1/lion/spec/get?_sid_=<UNKNOWN_SID_PARAM>`
5. `POST /app-portal/web/v1/session/get?_sid_=<UNKNOWN_SID_PARAM>`
6. `POST /app-portal/web/v1/user/<USER_ID>/get?_sid_=<UNKNOWN_SID_PARAM>`
7. `POST /app-portal/web/v1/user/profile/info?_sid_=<UNKNOWN_SID_PARAM>`
8. `GET /app-portal/web/v1/<RESOURCE>/copyright/get?_sid_=<UNKNOWN_SID_PARAM>&timestemp=<EPOCH_MS>`
9. `POST /app-portal/web/v1/user/<USER_ID>/list?_sid_=<UNKNOWN_SID_PARAM>`
10. `GET /app-portal/web/v1/user/category/app/resource/list?_sid_=<UNKNOWN_SID_PARAM>&basicType=<STRING>&timestemp=<EPOCH_MS>`
11. `POST /app-portal/web/v1/event/log/produce?_sid_=<UNKNOWN_SID_PARAM>`

Later Copy-as-cURL evidence confirms that working API requests send
`Authorization: Bearer <ACCESS_TOKEN>`. The bearer value matches the
`dtv_access_token` Local Storage value, not `access_token_key`,
`refresh_token_key`, `dtv_c_authn`, or `current_user_info`.

## Unresolved Authentication Questions

### Stage 1 `_sid_` Reinspection

All three HAR captures were reinspected in chronological request order.

Confirmed evidence:

- Capture 1 does not include a login POST. Its first observed `_sid_` appears
  on `POST /<APP_ID>/web/v1/user/app/asset/tree`.
- Capture 2 includes one `_sid_` request before the login POST:
  `GET /<APP_ID>/web/v1/logout?_sid_=<UNKNOWN_SID_PARAM>&timestemp=<EPOCH_MS>&withdrawConsent=<BOOL>`.
- Capture 3 starts at login and has no `_sid_` request before the login POST.
- The login POST URL query-key list is empty in captures 2 and 3. The login URL
  itself does not contain `_sid_`.
- The first post-login `_sid_` value in captures 2 and 3 was not found earlier
  in page/bootstrap requests, HTML or JavaScript response bodies, response
  headers, request headers, query parameters, request bodies, cookies, or
  referrer URLs captured by the HAR.
- The first post-login `_sid_` value was not present in the login request URL,
  request headers, or request body.
- No captured HTML or JavaScript response body referenced `_sid_`, `sid`, UUID
  generation, session creation logic, or the login endpoint in a way that
  explains how `_sid_` is generated.
- Each HAR uses multiple distinct `_sid_` values. `_sid_` is not constant
  throughout a session.
- Different `_sid_` values appear after logout/login and during later page or
  module loads.

Format characteristics:

- Observed `_sid_` values are short opaque URL-safe strings.
- Observed lengths are 9 or 13 characters.
- Values have no hyphens and do not match UUID text format.
- Values contain digits; some observed values are digit-only.
- This format does not prove whether values are client-generated or
  server-issued.

Inference:

- Because the first post-login `_sid_` value is absent from earlier HAR-visible
  data, `_sid_` is likely created by frontend runtime code or by browser state
  not captured in the HAR. This is an inference, not confirmed evidence.

Browser storage inspection needed:

Before and after a fresh login, inspect the following browser stores for
`home.istore.net.au`. Record only storage key names, value types, and value
lengths. Do not record actual values.

- Local Storage:
  - all key names
  - value type: string, JSON object, JSON array, number-like string, boolean-like
    string, opaque string
  - value length in characters
  - whether any key name contains `sid`, `session`, `token`, `user`, `app`,
    `org`, `login`, `route`, or `portal`
- Session Storage:
  - same key-name/type/length information as Local Storage
  - compare before login, immediately after login, and after opening the
    dashboard/chart pages
- IndexedDB:
  - database names
  - object store names
  - record counts
  - key names or key paths only
  - value type and approximate serialized length only
  - whether any database/store/key name contains `sid`, `session`, `token`,
    `user`, `app`, `org`, `login`, `route`, or `portal`

Do not copy browser storage values into the repository or chat.

### Browser Storage Metadata Comparison

Three browser storage metadata snapshots were inspected:

- before login
- after login
- after page refresh

The snapshots contain only key names, value types, value lengths, cookie names,
and IndexedDB database/store names. No storage values were inspected or copied.

Confirmed Local Storage findings:

- The before-login snapshot was not a fully clean browser state. It already
  contained authentication-looking keys:
  - `refresh_token_key`, string length 401
  - `dtv_access_token`, string length 45
  - `dtv_c_authn`, string length 20
- After login, these Local Storage keys appeared:
  - `access_token_key`, string length 45
  - `current_user_info`, string length 82
- After login, these Local Storage keys changed length:
  - `$SDK_LOG$`, string length changed
  - `login_url`, string length changed
  - `user_app_permission`, string length changed
  - `user_permission_type`, string length changed
- No Local Storage keys disappeared after login.
- After page refresh, `access_token_key`, `current_user_info`,
  `refresh_token_key`, `dtv_access_token`, and `dtv_c_authn` persisted with the
  same lengths. Only `$SDK_LOG$` changed length after refresh.

Confirmed Session Storage findings:

- After login, these Session Storage keys appeared:
  - `copyright_by_organization`, string length 121
  - `profile_info`, string length 4
  - `ouIpPathPatterns`, empty string
  - `multiple-asset-tree_<OPAQUE_TREE_ID>_APP_PORTAL_S_<OPAQUE_VALUE>_en-US`,
    string length 453
- No Session Storage keys disappeared after login.
- No Session Storage key lengths changed after refresh.
- Several `multiple-asset-tree_...` keys contain opaque key-name components.
  These are treated as sensitive identifiers even though they are key names.

Confirmed cookie findings:

- The only cookie name present in all three snapshots is `locale`.
- No new cookie names appeared after login.
- No authentication-looking cookie name was present in the metadata.

Confirmed IndexedDB findings:

- All three snapshots contain the same IndexedDB database and object store:
  - database: `MbrowserStorage`
  - version: 1
  - object store: `keyValuePairs`
- No IndexedDB database or object store appeared after login.
- Record-level IndexedDB key names and value lengths were not included in the
  provided metadata, so IndexedDB contents remain unknown.

Authentication-related key-name signals:

- Access-token candidates:
  - `access_token_key`
  - `dtv_access_token`
- Refresh-token candidate:
  - `refresh_token_key`
- Authentication/session-state candidate:
  - `dtv_c_authn`
- User-state candidates:
  - `current_user_info`
  - `current_user`
  - `hossainUserInfo`
  - `user_app_permission`
  - `user_permission_type`
  - `user_dev_permission`
- App/bootstrap-state candidates:
  - `dtv_lion_config`
  - `working_org_key`
  - `working_app_id`
  - `working_menu_code`
  - `working_portal_type`
  - `working_nav_mode`
  - `siteMeta`
  - `deviceMeta`
  - `assetType`
  - `unitConfig`
  - `dtv_unit_config`
  - `dtv_ns_k`
  - `dtv_ns_info_encompass`
  - `multiple-asset-tree_<OPAQUE_TREE_ID>_APP_PORTAL_S_<OPAQUE_VALUE>_en-US`
- Encryption/signing material:
  - No key name strongly indicates encryption keys, signing keys, HMAC secrets,
    or request-signing material.

Confirmed persistence after refresh:

- The authentication-looking Local Storage keys persisted after refresh:
  `access_token_key`, `dtv_access_token`, `refresh_token_key`, and
  `dtv_c_authn`.
- User/bootstrap keys also persisted after refresh.
- Session Storage keys added after login also persisted across the tested page
  refresh, which indicates the same browser tab/session was retained.

Inference:

- Authentication most likely depends on Local Storage, not cookies. This is
  inferred from persistent token-looking Local Storage keys and the absence of
  authentication-looking cookie names.
- Session Storage appears to hold portal UI/bootstrap state, especially
  organization/copyright/profile and asset-tree cache entries.
- IndexedDB may hold additional key/value data, but the provided metadata only
  included database and object-store names, so it cannot yet be ruled in or out.
- Because `_sid_` changes within a single HAR, does not appear in storage key
  names, is not cookie-backed, and is absent from the login URL/body/headers,
  it is less likely to be the main authenticated-session value. It is more
  likely to be a request/module nonce, cache/routing value, correlation value,
  or frontend-generated bootstrap parameter. This is an inference only.
- Later working-request evidence proves that `dtv_access_token` is usable
  directly as a bearer token for API requests after the token exists.
  Browser-side transformation is still unresolved for the login password and
  token-creation step.

Minimum next evidence:

- A storage metadata snapshot from a truly clean state: all site Local Storage,
  Session Storage, IndexedDB, and cookies cleared before visiting the portal.
- IndexedDB record metadata for `MbrowserStorage/keyValuePairs`: key names,
  value types, and value lengths only.
- For one successful `asset/list` or `asset/detail` request after login, a
  sanitized request-header inventory that includes header names and value
  lengths only, not values. This should confirm whether any header length
  matches `access_token_key`, `dtv_access_token`, `refresh_token_key`, or
  `dtv_c_authn`.
- A controlled token-removal observation using the browser only:
  remove or rename one token-looking Local Storage key at a time, refresh, and
  record whether the portal stays authenticated. Do not record token values.

## Frontend Authentication Transport Analysis

All JavaScript response bodies and other frontend assets available inside the
three HAR files were searched for these names and concepts:
`access_token_key`, `dtv_access_token`, `refresh_token_key`, `dtv_c_authn`,
`current_user_info`, `_sid_`, `sid`, `Authorization`, `Bearer`, `token`,
`login`, `refresh`, request interceptors, Axios, Fetch, and XMLHttpRequest.

Confirmed HAR-content limitations:

- The three HAR files contain JSON/XHR responses, but no JavaScript or HTML
  response bodies were embedded in the captures.
- Therefore, no bundled frontend source code was available in the HARs to prove
  which module reads `access_token_key`, `dtv_access_token`,
  `refresh_token_key`, `dtv_c_authn`, or `current_user_info`.
- No source maps were present in the HAR response bodies.
- No readable bundled code was available to inspect for `axios.interceptors`,
  `fetch`, `XMLHttpRequest`, UUID utilities, signing utilities, encryption, or
  direct storage reads.

Confirmed initiator evidence:

- All captured API requests have script initiators.
- Initiator stacks reference minified frontend bundles such as:
  - `/static/js/vendors~main.<HASH>.chunk.js`
  - `/static/js/vendor~main~<HASH>.<HASH>.chunk.js`
  - `/static/js/main.<HASH>.chunk.js`
  - route chunks such as `/static/js/7.<HASH>.chunk.js` and
    `/static/js/37.<HASH>.chunk.js`
- Common stack function names include `xhr` and `request` in vendor bundles.
- Application-level function names observed in stacks include:
  - `assetList`
  - `assetDetail`
  - `getUserInfo`
- This confirms an XHR-based request wrapper. The stack shape is consistent
  with Axios-style XHR transport, but the bundled source bodies are not present,
  so Axios itself and any interceptor logic are not confirmed from code.

Confirmed request-header and request-parameter evidence:

- The original HAR parser did not expose token values in later API requests.
- Later Copy-as-cURL evidence confirms that working API calls do use
  `Authorization: Bearer <ACCESS_TOKEN>`.
- The bearer value exactly matches the Local Storage value named
  `dtv_access_token`.
- The bearer value does not match `access_token_key`, `refresh_token_key`,
  `dtv_c_authn`, or `current_user_info`.
- No working API request places the refresh token, authentication-state value,
  or current-user object in a query parameter, request body, or custom header.
- Common Home/monitor API requests use ordinary browser headers plus
  `locale` or `Locale`, and add the bearer `Authorization` header.
- App-portal requests use `_sid_` as a query parameter on selected endpoints.
- Data-service or metadata-style requests use `appId` and `PermissionAppId`
  headers, both with UUID-length values. These look like app/routing/permission
  identifiers, not bearer tokens.
- Dashboard widget requests to
  `POST /<APP_ID>/datasource/v2/data/query?_p=<OPAQUE_QUERY_VALUE>` use:
  - `X-APPID`, UUID-length value
  - `X-NS`, short namespace-like value
  - `X-CK`, short value
- `X-CK` appears only on the dashboard data-query endpoint in the captures. Its
  role is not proven. It may be a dashboard SDK context/cache key, but this is
  an inference.

Confirmed authentication-adjacent request sequence:

```text
GET  /<APP_ID>/framework/v1.0/user/public-key
POST /<APP_ID>/framework/v1.0/user/login
POST /<APP_ID>/framework/v1.0/user/<USER_ID>
POST /<APP_ID>/web/v1/user/app/asset/tree?_sid_=<UNKNOWN_SID_PARAM>&...
POST /<APP_ID>/web/v1/session/get?_sid_=<UNKNOWN_SID_PARAM>
GET  /<APP_ID>/user/v1.0/user-info
```

- The `public-key` endpoint is captured before login. This suggests the login
  password may be encrypted or transformed by the frontend before submission,
  but the HAR evidence does not prove the algorithm.
- The login response body is empty.
- The post-login `framework/v1.0/user/<USER_ID>` response body is empty.
- `user-info` returns a `token` field in HAR responses. The current working
  Local Storage token did not appear verbatim in the three older HAR response
  bodies, so the exact relationship between `user-info.data.token` and
  `dtv_access_token` is not proven from these files.

Confirmed `_sid_` evidence:

- Because `_sid_` changes within a single HAR, it is documented as
  `<UNKNOWN_SID_PARAM>`, not as a session ID.
- No HAR-embedded frontend source explains `_sid_` generation.
- The first post-login `_sid_` value is not visible earlier in HAR request URLs,
  response headers, request headers, request bodies, response bodies, cookies,
  or referrer URLs.
- `_sid_` values are short URL-safe strings, not UUID-shaped.

Confirmed `dtv_c_authn` evidence:

- `dtv_c_authn` exists in Local Storage before login and persists after login
  and refresh.
- Its key name strongly suggests authentication state or authentication metadata.
- Its value length is short compared with token-looking keys.
- Without value inspection or source code, it cannot be classified as a boolean
  flag, token metadata, encryption key, or authentication scheme identifier.

Confirmed refresh-token evidence:

- `refresh_token_key` exists in Local Storage before login and persists after
  login and refresh.
- No HAR or working Copy-as-cURL request clearly calls a refresh-token endpoint
  or visibly sends the refresh token.
- `web/v1/session/get` returns expiry and refresh/create time metadata, but it
  does not prove token refresh transport.

Inferences:

- The portal likely uses an XHR wrapper from a minified vendor bundle, probably
  Axios-style, but this is not confirmed by source text.
- Authentication for working API calls depends on a Local Storage access-token
  value sent as a bearer token.
- The portal may still require frontend password encryption or token/bootstrap
  steps before the bearer token exists.
- `_sid_` is more likely a frontend-generated or SDK-generated request/module
  parameter than the main authenticated-session value. This remains inference.

Unresolved:

- Which exact JavaScript module reads `access_token_key` or `dtv_access_token`.
- Whether an Axios interceptor or custom SDK interceptor adds hidden headers or
  parameters before HAR serialization.
- Whether `X-CK` is derived from dashboard state, request body, or a static
  runtime SDK context.
- Whether `_sid_` is random, timestamp-derived, token-derived, or returned by a
  backend/bootstrap call not visible in the HAR.
- Whether login password encryption uses the captured `public-key` endpoint,
  and if so what algorithm/padding/encoding is required.

Minimum next manual browser inspection:

- In DevTools Sources, search loaded scripts for exact strings:
  `access_token_key`, `dtv_access_token`, `refresh_token_key`, `dtv_c_authn`,
  `_sid_`, `X-CK`, `Authorization`, `Bearer`, `set-session`, and
  `public-key`.
- If source maps are available in the browser, record only source file/module
  names and function names that read those keys.
- In DevTools, set breakpoints or logpoints on:
  - `localStorage.getItem`
  - `sessionStorage.getItem`
  - `XMLHttpRequest.prototype.open`
  - `XMLHttpRequest.prototype.setRequestHeader`
  - `XMLHttpRequest.prototype.send`
  - `window.fetch`
- For one `asset/list` or `asset/detail` call, record only:
  - header names
  - header value lengths
  - query key names
  - body key names
  - whether any header/query/body value length matches
    `access_token_key`, `dtv_access_token`, `refresh_token_key`, or
    `dtv_c_authn`
- For one `_sid_`-bearing request, record which function created or assigned
  the `_sid_` query key, if a breakpoint can identify it. Do not record the
  value.

### Runtime Request Log Comparison

A Chrome runtime log produced by XMLHttpRequest/fetch wrappers was inspected.
The file also contained ordinary console output and page URLs, so all findings
below are reported with identifiers and values redacted.

Confirmed limitations:

- The runtime log did not contain the expected structured wrapper records for
  XHR/fetch request metadata.
- No runtime entries exposed header-name/value-length tables for individual API
  requests.
- No runtime entries exposed query-key/value-length tables for individual API
  requests.
- No runtime entries exposed body-key/value-type/value-length tables beyond
  ordinary console output.
- The strings `X-CK`, `X-APPID`, `X-NS`, `_sid_`, `fetch`, `XMLHttpRequest`,
  and wrapper-style labels such as `headers`, `query`, or `body` were not
  present as structured request-log fields.

Confirmed runtime clues:

- A frontend page URL for the Hossain site view contains an `accessToken` query
  key.
- The `accessToken` query value length is 45 characters, matching the known
  Local Storage lengths for `access_token_key` and `dtv_access_token`.
- The same frontend page URL also contains app/site routing state such as
  `appId`, `menuCode`, `categoryId`, `locale`, `state`, and a timer-like query
  parameter. Identifying values are redacted.
- Console output confirms frontend route/bootstrap concepts such as app start,
  site view parameters, locale reads, page cache service, data service init, and
  data worker init.
- The runtime log did not show `refresh_token_key` length 401 or `dtv_c_authn`
  length 20 being sent in a header, query parameter, or request body.

Comparison with stored auth metadata:

- `access_token_key`: length 45 in Local Storage; runtime page URL has
  `accessToken` length 45.
- `dtv_access_token`: length 45 in Local Storage; runtime page URL has
  `accessToken` length 45.
- `refresh_token_key`: length 401 in Local Storage; no matching runtime
  request metadata observed.
- `dtv_c_authn`: length 20 in Local Storage; no matching runtime request
  metadata observed.
- `X-CK`: observed in HARs only on dashboard `datasource/v2/data/query`
  requests; not present in the runtime log.
- `X-APPID` and `X-NS`: observed in HARs on dashboard/help/data-service
  requests; not present in the runtime log.
- `_sid_`: observed in HARs on selected app-portal requests; not present in
  the runtime log.

Confirmed answers from the runtime log:

- Runtime-added API headers cannot be determined from this log because the
  structured wrapper output is absent.
- Header/query/body value-length matches for API requests cannot be determined
  from this log.
- `X-CK` constancy cannot be determined from this log. HAR evidence only shows
  that `X-CK` appears on dashboard data-query requests with a short value.
- `_sid_` occurrence cannot be measured from this runtime log. HAR evidence
  still shows `_sid_` only on selected app-portal endpoints, not every request.
- XHR versus fetch authentication differences cannot be determined from this
  log.
- Request-body mutation cannot be determined from this log.

Inference:

- The strongest new clue is that the frontend site-view app is bootstrapped with
  a 45-character `accessToken` query parameter that matches the known
  access-token storage lengths.
- This suggests the portal shell may pass the access token into the embedded or
  routed Hossain frontend via URL bootstrap state, after which the frontend or
  SDK establishes request context.
- Later Copy-as-cURL evidence proves the backend APIs accept the stored
  `dtv_access_token` value as a bearer token.

### Working Copy-as-cURL Authentication Evidence

Private Copy-as-cURL output and private Local Storage values were compared
locally. Real token values, cookies, account identifiers, and IDs are not
recorded here.

Confirmed stored-value usage:

| Stored value | Observed in working API requests | Role |
| --- | --- | --- |
| `dtv_access_token` | Yes | Sent as `Authorization: Bearer <ACCESS_TOKEN>` |
| `access_token_key` | No exact match | Token-looking Local Storage value, not observed in requests |
| `refresh_token_key` | No exact match | Stored refresh-token candidate, not sent in captured requests |
| `dtv_c_authn` | No exact match | Stored auth-state/auth-scheme candidate, not sent in captured requests |
| `current_user_info` | No exact match | Stored user metadata object, not sent in captured requests |

Confirmed transport by endpoint family:

| Endpoint family | Auth transport | Other context |
| --- | --- | --- |
| `POST /hossain-bff/monitor/v1.0/asset/list` | `Authorization: Bearer <ACCESS_TOKEN>` | `locale` header |
| `POST /hossain-bff/monitor/v1.0/asset/detail` | `Authorization: Bearer <ACCESS_TOKEN>` | `locale` header |
| `GET /hossain-bff/user/v1.0/user-info` | `Authorization: Bearer <ACCESS_TOKEN>` | `locale` header |
| `POST /app-portal/web/v1/user/app/asset/tree` | `Authorization: Bearer <ACCESS_TOKEN>` | `_sid_`, `appId`, `needAssociateAsset`, `resourceTypes`, `Locale` header |
| `POST /dt-service/datasource/v2/data/query` | `Authorization: Bearer <ACCESS_TOKEN>` | `_p` query key plus `X-APPID`, `X-NS`, and `X-CK` headers |
| `POST /hossain-bff/framework/v1.0/user/login` | No bearer token | Body keys `account`, `password`, `strategy` |

Confirmed `_sid_` findings from working requests:

- `_sid_` appears on the app-portal asset-tree request family, not on every
  authenticated API request.
- `_sid_` is absent from the working login, user-info, asset-list,
  asset-detail, and data-query requests.
- Four working asset-tree requests used four distinct `_sid_` values.
- Working `_sid_` values are opaque, URL-safe, 13-character strings.
- `_sid_` does not exactly match any inspected Local Storage authentication
  value and does not share the token lengths.

Inference:

- `_sid_` is most likely a per-request or per-module frontend nonce,
  correlation value, cache/routing value, or app-portal bootstrap parameter. It
  is not the bearer-token credential and should not be treated as the primary
  authenticated session value.

Confirmed `X-CK`, `X-APPID`, and `X-NS` findings from working requests:

- `X-APPID` appears only on `datasource/v2/data/query` working requests and has
  a UUID-length value. It is most likely the dashboard/app context identifier.
- `X-NS` appears only on `datasource/v2/data/query` working requests and has a
  short namespace-like value. It is most likely a data-service namespace.
- `X-CK` appears only on `datasource/v2/data/query` working requests. Its value
  length is short and was constant across the inspected working data-query
  requests.
- None of these three header values exactly matches `dtv_access_token`,
  `access_token_key`, `refresh_token_key`, `dtv_c_authn`, or
  `current_user_info`.

Inference:

- `X-APPID`, `X-NS`, and `X-CK` are dashboard data-service context headers, not
  the primary authentication credential.
- Because `X-CK` was constant across the inspected working data-query requests,
  it may be a static context key or SDK/config value for the dashboard data
  source. Its origin is still not proven.

Login and refresh-token evidence:

- The working login request does not send an `Authorization` header.
- The working login request body contains `account`, `password`, and
  `strategy`.
- The working login `password` value is long and base64-like. This indicates
  frontend encryption or transformation before submission.
- HAR captures show `GET /hossain-bff/framework/v1.0/user/public-key` before login
  in one flow, which is consistent with password encryption, but the
  algorithm/padding/encoding are not proven.
- Successful login and `set-session` responses are empty in the HAR captures
  and do not set cookies or redirect.
- No working request sends `refresh_token_key`, and no refresh endpoint was
  observed. A refresh-token flow is not required for short-lived experimental
  polling after login/token acquisition, but it will probably be required for a
  robust integration.

Confirmed reproducibility boundary:

- Once `<ACCESS_TOKEN>` is available, the live and historical API requests
  appear reproducible with `aiohttp` without a browser by sending
  `Authorization: Bearer <ACCESS_TOKEN>` and the same sanitized JSON body
  shapes documented below.
- Login is not fully reproducible yet because the password transformation and
  exact token-creation path remain unresolved.

Minimum request sequence inferred from working evidence:

1. Login/token acquisition:
   - `GET /hossain-bff/framework/v1.0/user/public-key`
   - transform password according to the frontend login algorithm
   - `POST /hossain-bff/framework/v1.0/user/login`
   - `POST /hossain-bff/framework/v1.0/user/set-session`
   - obtain or persist `dtv_access_token` as `<ACCESS_TOKEN>`
2. Authentication bootstrap:
   - `POST /app-portal/web/v1/user/app/asset/tree?...&_sid_=<UNKNOWN_SID_PARAM>`
   - optional `POST /app-portal/web/v1/session/get?_sid_=<UNKNOWN_SID_PARAM>`
   - `GET /hossain-bff/user/v1.0/user-info`
3. Site discovery:
   - `POST /hossain-bff/monitor/v1.0/asset/list`
   - `POST /hossain-bff/monitor/v1.0/asset/detail`
4. Live telemetry:
   - poll `asset/list` and `asset/detail` using the bearer token and relevant
     discovered IDs.
5. Historical/dashboard telemetry:
   - `POST /hossain-bff/monitor/v1.0/measurement-point/time-series` for direct
     time-series where available.
   - `POST /dt-service/datasource/v2/data/query?_p=<OPAQUE_QUERY_VALUE>` with
     `X-APPID`, `X-NS`, and `X-CK` for dashboard batch queries where required.

Evidence still missing before implementing full login:

- The frontend password transformation algorithm for the `login` request.
- Whether `dtv_access_token` is returned by a hidden response, created by the
  portal shell, produced by `set-session`, or copied from `user-info.data.token`
  in the same login generation.
- The exact source of `X-CK` for data-query requests.
- The refresh endpoint and refresh request/response shape.

1. **Login response headers**
   - The captured successful login responses have HTTP `200`, no response body, no observed
     `Location` header, and no observed `Set-Cookie` values.
   - The immediately following `POST /<APP_ID>/framework/v1.0/user/<USER_ID>`
     response is also empty in capture 3.
   - The HAR does not expose browser storage or JavaScript runtime state, so
     the exact client-side creation of `_sid_` remains unresolved.

2. **Where `_sid_` first appears**
   - Capture 1 begins already authenticated. The first observed `_sid_` appears
     on `POST /<APP_ID>/web/v1/user/app/asset/tree`.
   - Capture 2 starts with a logout request containing `_sid_`, then later
     captures login. After login, the first observed post-login `_sid_` in that
     capture appears on `POST /<APP_ID>/web/v1/lion/get`.
   - Capture 3 starts at login with preserved logging. The first observed
     post-login `_sid_` appears on
     `POST /<APP_ID>/web/v1/user/app/asset/tree`.
   - `_sid_` was not observed in the login response URL, a redirect target, a
     `Location` response header, or a `Set-Cookie` response.
   - Browser storage and JavaScript runtime state were not captured directly.

3. **Exact sanitized post-login sequence**
   - See the ordered list in "Authentication And Session Flow". The first
     post-login request that uses `_sid_` is:

     ```text
     POST /<APP_ID>/web/v1/user/app/asset/tree?_sid_=<UNKNOWN_SID_PARAM>&appId=<APP_ID>&needAssociateAsset=<BOOL>&resourceTypes=<STRING>
     ```

4. **Whether `_sid_` remains constant throughout each HAR**
   - No. Multiple distinct `_sid_` values were observed inside each HAR.
   - Treat `_sid_` as an opaque sensitive value. It may represent per-app,
     per-module, nonce, cache, or regenerated bootstrap state rather than one
     stable session identifier.

5. **Whether the HAR files use different `_sid_` values**
   - Yes. The captures use different sets of `_sid_` values. Capture 3 also
     contains multiple distinct `_sid_` values.

6. **Expiry, timeout, refresh, logout, or session validity information**
   - `POST /<APP_ID>/web/v1/session/get?_sid_=<UNKNOWN_SID_PARAM>` returns session
     metadata with keys:

     ```json
     {
      "id": "<OPAQUE_SESSION_METADATA_ID>",
       "expires": 3600,
       "user": {
         "id": "<USER_ID>",
         "name": "<STRING>",
         "description": "<STRING>",
         "theme": "<STRING>",
         "domain": "<STRING>",
         "email": "<EMAIL>"
       },
       "workingOrganization": {
         "id": "<ORG_ID>",
         "name": "<STRING>",
         "code": "<STRING>",
         "description": "<STRING>",
         "languages": ["<STRING>"]
       },
       "refreshTime": 1767222245000,
       "createTime": 1767222000000,
       "mfaType": "<STRING>",
       "isSsoLogin": false,
       "adminLevel": 0,
       "hasAppPermission": true,
       "hasDevPermission": null,
       "MFACompleted": true,
       "generatedByRefreshToken": "<REDACTED>",
       "countMessageType": [1]
     }
     ```

   - `GET /<APP_ID>/web/v1/logout?_sid_=<UNKNOWN_SID_PARAM>&timestemp=<EPOCH_MS>&withdrawConsent=<BOOL>`
     was observed.

7. **Unauthenticated or expired session response**
   - Invalid-login and expired-session application responses were still not
     captured. HAR status `0` appears on some requests, but those are not
     reliable evidence of an application-level unauthenticated response.

8. **Whether the user-info token is used later**
   - The older HAR captures did not show token replay.
   - Later working-request evidence confirms `Authorization: Bearer
     <ACCESS_TOKEN>` on API requests, but the current working Local Storage
     token did not appear verbatim in the older HAR `user-info` responses.
     Therefore, the exact relationship between `user-info.data.token` and
     `dtv_access_token` remains unresolved.

## Endpoint Dependency Graph

```text
login
  -> POST /<APP_ID>/framework/v1.0/user/login
  -> POST /<APP_ID>/framework/v1.0/user/<USER_ID>
  -> POST /<APP_ID>/web/v1/lion/get?_sid_=<UNKNOWN_SID_PARAM>
  -> POST /<APP_ID>/web/v1/session/get?_sid_=<UNKNOWN_SID_PARAM>
       -> yields session metadata, <USER_ID>, <ORG_ID>-like organization data
  -> GET /<APP_ID>/user/v1.0/user-info
       -> yields user/account metadata and <ACCESS_TOKEN>-like field
  -> POST /<APP_ID>/web/v1/user/app/asset/tree?...&_sid_=<UNKNOWN_SID_PARAM>
       -> yields asset tree and structure relationships
  -> GET /<APP_ID>/monitor/v1.0/asset/type
       -> yields available asset/model types
  -> GET /<APP_ID>/monitor/v1.0/meta/generic?mdmTypes=<MDM_TYPES>
       -> yields measurement point and metric metadata
  -> POST /<APP_ID>/monitor/v1.0/asset/list
       -> discovers site/device assets and live summary points
  -> POST /<APP_ID>/monitor/v1.0/asset/detail
       -> fetches current site/device telemetry
  -> POST /<APP_ID>/monitor/v1.0/measurement-point/time-series
       -> fetches chart/history rows for selected measurement points and dates
  -> POST /<APP_ID>/<NAMESPACE>/<NAMESPACE>/v1.0/<RESOURCE>?groups=<GROUPS>
       -> fetches time-series or grouped measurement data
  -> POST /<APP_ID>/datasource/v2/data/query?_p=<OPAQUE_QUERY_VALUE>
       -> dashboard-widget data batch used by chart pages
```

Observed dependencies:

- `<UNKNOWN_SID_PARAM>` appears as `_sid_` on web bootstrap endpoints.
- `<SITE_ID>` and `<DEVICE_ID>`-like values originate from asset tree, asset
  list, and asset detail responses.
- Measurement point names originate from `monitor/v1.0/meta/generic` and are
  reused in `asset/list`, `asset/detail`, and time-series requests.
- Time-series requests use `siteGroups` and `measurementPointInfos`.

## Site And Device Discovery

Relevant endpoints:

```text
POST /<APP_ID>/web/v1/user/app/asset/tree
GET  /<APP_ID>/web/v1/user/app/structure/get
GET  /<APP_ID>/web/v1/user/structure/detail/get
GET  /<APP_ID>/monitor/v1.0/asset/type
POST /<APP_ID>/monitor/v1.0/asset/list
POST /<APP_ID>/monitor/v1.0/asset/detail
```

Observed asset types:

- `Res_Solar_Site`
- `Res_Inverter`
- `Res_Storage`
- `Res_Meter`
- `Dongle`

Observed asset attributes include redacted identifiers and descriptive metadata:

```json
{
  "mdmId": "<DEVICE_ID>",
  "mdmType": "Res_Inverter",
  "attributes": {
    "mdmType": "Res_Inverter",
    "modelId": "<MODEL_ID>",
    "timezone": "Australia/Perth",
    "displayOrder": 1,
    "mdmPath": "<REDACTED_PATH>",
    "modelIdPath": "<REDACTED_PATH>",
    "parentId": "<SITE_ID>",
    "modelName": "<STRING>",
    "name": "<DEVICE_NAME>",
    "sn": "<SERIAL_NUMBER>",
    "rootModelId": "<MODEL_ID>",
    "topoParentDeviceID": "<DEVICE_ID>"
  }
}
```

Site detail attributes may include address, contact, latitude, longitude, NMI,
network provider, and other personal or identifying data. These must be
redacted in diagnostics and never logged raw.

## Current And Live Telemetry Endpoints

Primary live endpoints:

```text
POST /<APP_ID>/monitor/v1.0/asset/list
POST /<APP_ID>/monitor/v1.0/asset/detail
```

Observed request keys:

```json
{
  "pageSize": 10,
  "pageNo": 1,
  "mdmIds": "<SITE_OR_DEVICE_ID_LIST>",
  "mdmTypes": "<MDM_TYPE_LIST>",
  "measurementPoints": "<MEASUREMENT_POINT_LIST>",
  "attributes": "<ATTRIBUTE_LIST>",
  "view": "<VIEW_NAME>"
}
```

Response shape:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "mdmId": "<DEVICE_ID>",
      "mdmType": "Res_Inverter",
      "attributes": {},
      "measurementPoints": {
        "INV.GenActivePW": {
          "timestamp": 1767222245000,
          "localtime": "2026-01-02 03:04:05",
          "value": 4.2,
          "attributes": {}
        }
      }
    }
  ],
  "requestId": "<REQUEST_ID>",
  "pagination": {
    "pageNo": 1,
    "pageSize": 10,
    "totalSize": 1
  }
}
```

`asset/detail` can also return `data` as an object keyed by redacted asset ID:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "<SITE_ID>": {
      "attributes": {},
      "metrics": {},
      "measurementPoints": {}
    }
  },
  "requestId": "<REQUEST_ID>"
}
```

## Historical And Accumulated-Energy Endpoints

Observed metadata endpoints:

```text
GET  /<APP_ID>/monitor/v1.0/meta/generic?mdmTypes=<MDM_TYPES>
POST /<APP_ID>/<NAMESPACE>/<NAMESPACE>/v1.0/metadata?ifMerge=<BOOL>&withI18n=<BOOL>
```

Observed chart/history endpoint:

```text
POST /<APP_ID>/monitor/v1.0/measurement-point/time-series
```

Request shape:

```json
{
  "mdmTypes": "Res_Storage",
  "mdmIds": "<DEVICE_ID>",
  "startTime": "2026-01-02 00:00:00",
  "endTime": "2026-01-03 00:00:00",
  "interval": "5m",
  "measurementPoints": "BS.TotalChargingEng,BS.ChargingEngDay,BS.DischargingEngDay,BS.TotalDischargingEng",
  "autoInterpolate": true
}
```

Response shape:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "localtime": "2026-01-02 03:04:05",
      "timestamp": 1767222245000,
      "mdmId": "<DEVICE_ID>",
      "BS.TotalChargingEng": 1234.5,
      "BS.ChargingEngDay": 6.7,
      "BS.DischargingEngDay": 4.2,
      "BS.TotalDischargingEng": 987.6
    }
  ],
  "requestId": "<REQUEST_ID>"
}
```

Other observed `measurement-point/time-series` examples request inverter
history such as `INV.APProduction` and electrical details such as phase
voltages. Request date fields use local site time strings in
`YYYY-MM-DD HH:MM:SS` format. Response rows also include `timestamp` as epoch
milliseconds and `localtime` as local site time.

Observed dashboard-widget batch endpoint:

```text
POST /<APP_ID>/datasource/v2/data/query?_p=<OPAQUE_QUERY_VALUE>
```

Request body shape:

```json
[
  {
    "dcKey": "<DASHBOARD_WIDGET_KEY>",
    "datasourceId": "<DASHBOARD_DATASOURCE_ID>",
    "internalKey": "<DASHBOARD_INTERNAL_KEY>",
    "category": "<STRING>",
    "pagination": {
      "pageSize": 1000,
      "pageNum": 1,
      "enablePagination": false
    },
    "fields": ["localtime", "ActiveProduction", "SelfConsProduction"],
    "params": {
      "startTime": "2026-01-02 00:00:00",
      "endTime": "2026-01-03 00:00:00",
      "interval": "D",
      "autoData": "<STRING>",
      "aggregation": "<STRING>",
      "rawAttribute": "<STRING>",
      "mdmId": "<SITE_ID>",
      "preserveIndex": "<STRING>",
      "autoInterpolate": "<STRING>",
      "newType": "<STRING>"
    },
    "filters": [],
    "fieldMetaMap": {},
    "sort": [
      {
        "field": "localtime",
        "sorted": "asc"
      }
    ],
    "aggregation": false
  }
]
```

Response body shape:

```json
{
  "code": 200,
  "msg": "success",
  "subMsg": null,
  "data": {
    "<DASHBOARD_WIDGET_KEY>": {
      "calculateFields": [],
      "data": [
        {
          "localtime": "2026-01-02 00:00:00",
          "ActiveProduction": 12.3,
          "SelfConsProduction": 8.4,
          "OnGridEnergy": 3.9,
          "mdmId": "<SITE_ID>"
        }
      ],
      "fields": ["localtime", "ActiveProduction", "SelfConsProduction"],
      "meta": {},
      "message": null,
      "subMessage": null,
      "callInfo": {},
      "datasourceDTO": {
        "id": "<DASHBOARD_DATASOURCE_ID>",
        "name": "<STRING>",
        "internalKey": "<DASHBOARD_INTERNAL_KEY>"
      },
      "dcKey": "<DASHBOARD_WIDGET_KEY>",
      "pagination": {
        "pageSize": 1000,
        "pageNum": 1,
        "totalSize": 1,
        "enablePagination": false
      }
    }
  }
}
```

The direct `measurement-point/time-series` endpoint is simpler and better
suited for an integration than the dashboard-specific batch endpoint.

Metadata and chart responses distinguish daily and lifetime fields:

- Daily energy fields: `BS.ChargingEngDay`, `BS.DischargingEngDay`,
  `ActiveProduction:TD`, `TotalActiveProduction:TD`,
  `StorageChargeProduction:TD`, `StorageDischargeProduction:TD`.
- Lifetime/cumulative candidates: `BS.TotalChargingEng`,
  `BS.TotalDischargingEng`, `TotalActiveProduction:BOL`,
  `StorageChargeProduction:BOL`, `StorageDischargeProduction:BOL`,
  `BESSChargeEnergy:BOL`, `BESSDischargeEnergy:BOL`.
- The new capture shows lifetime-style field names and `BOL` metadata, but the
  sampled rows do not by themselves prove monotonic behavior across restarts,
  days, or API refreshes. Energy Dashboard suitability remains provisional.

## Sanitized Request Schemas

Login:

```json
{
  "strategy": "<STRING>",
  "account": "<EMAIL_OR_ACCOUNT>",
  "password": "<ENCRYPTED_OR_TRANSFORMED_PASSWORD>"
}
```

Session get:

```text
POST /<APP_ID>/web/v1/session/get?_sid_=<UNKNOWN_SID_PARAM>
```

Lion config:

```json
{
  "keys": ["<CONFIG_KEY>"]
}
```

Asset tree:

```text
POST /<APP_ID>/web/v1/user/app/asset/tree?_sid_=<UNKNOWN_SID_PARAM>&appId=<APP_ID>&needAssociateAsset=<BOOL>&resourceTypes=<STRING>
```

Asset list:

```json
{
  "pageSize": 10,
  "pageNo": 1,
  "mdmIds": "<SITE_OR_PARENT_ID_LIST>",
  "mdmTypes": "Res_Inverter,Res_Storage,Res_Meter,Dongle",
  "measurementPoints": "DeviceState",
  "view": "<VIEW_NAME>"
}
```

Asset detail:

```json
{
  "mdmIds": "<SITE_OR_DEVICE_ID_LIST>",
  "attributes": "<ATTRIBUTE_LIST>",
  "measurementPoints": "PUB_SITE.PVOutputPower,PUB_SITE.METERActivePW,PUB_SITE.BSActivePW,PUB_SITE.Soc"
}
```

Metadata:

```text
GET /<APP_ID>/monitor/v1.0/meta/generic?mdmTypes=<MDM_TYPES>
```

Time series:

```json
{
  "mdmTypes": "Res_Storage",
  "mdmIds": "<DEVICE_ID>",
  "startTime": "2026-01-02 00:00:00",
  "endTime": "2026-01-03 00:00:00",
  "interval": "5m",
  "measurementPoints": "BS.TotalChargingEng,BS.ChargingEngDay,BS.DischargingEngDay,BS.TotalDischargingEng",
  "autoInterpolate": true
}
```

## Sanitized Response Schemas

Generic success response:

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "requestId": "<REQUEST_ID>"
}
```

Some endpoints use:

```json
{
  "code": 200,
  "msg": "success",
  "data": {},
  "globalTraceId": "<TRACE_ID>"
}
```

User info:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "userId": "<USER_ID>",
    "username": "<USERNAME>",
    "orgId": "<ORG_ID>",
    "orgName": "<ORG_NAME>",
    "token": "<ACCESS_TOKEN>",
    "locale": "en-US",
    "email": "<EMAIL>",
    "phone": "<PHONE>",
    "phoneArea": "<PHONE_AREA>",
    "companyId": "<ORG_ID>",
    "role": 1,
    "enable": 1,
    "uri": "<URI>"
  },
  "requestId": "<REQUEST_ID>"
}
```

Measurement metadata:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "attribute": [
      {
        "mdmType": "Res_Solar_Site",
        "modelId": "<MODEL_ID>",
        "name": "<STRING>",
        "attribute": "<ATTRIBUTE_NAME>",
        "units": "<UNIT_OR_NULL>",
        "source": "<STRING>",
        "type": "STRING"
      }
    ],
    "measurementPoint": [
      {
        "mdmType": "Res_Solar_Site",
        "modelId": "<MODEL_ID>",
        "mdmAggMethods": "sum",
        "units": "kW",
        "source": "<STRING>",
        "type": "DOUBLE",
        "timeAggMethods": "avg,sum,max,min,first,last",
        "hasTimeSeries": true,
        "accumulable": false,
        "signalType": "AI",
        "name": "Site PV Active Power",
        "interval": "RAW,1m,5m,10m,15m,30m,60m",
        "measurementPoint": "PUB_SITE.PVOutputPower"
      }
    ],
    "metric": [
      {
        "period": "TD",
        "mdmType": "Res_Solar_Site",
        "paasMetric": "<METRIC_BACKING_FIELD>",
        "units": "kWh",
        "type": "DOUBLE",
        "metric": "ActiveProduction:TD",
        "name": "Production Today",
        "interval": null,
        "standardType": "<STRING>"
      }
    ]
  },
  "requestId": "<REQUEST_ID>"
}
```

## Telemetry Fields, Units, And Types

Observed live fields relevant to Home Assistant:

| Field | Meaning from metadata or context | Type | Unit | Notes |
| --- | --- | --- | --- | --- |
| `PUB_SITE.PVOutputPower` | Site PV active/output power | int/float | `kW` | Instantaneous |
| `SITE.GenActivePW` | Site active power / production power | int/float | `kW` | Instantaneous |
| `INV.GenActivePW` | Inverter active power | int/float | `kW` | Instantaneous |
| `ConsPower` | Total load/consumption power | float | `kW` | Instantaneous |
| `PUB_SITE.METERActivePW` | Grid/site meter active power | float | `kW` | Sign convention unresolved |
| `METER.ActivePW` | Meter active power | float | `kW` | Sign convention unresolved |
| `PUB_SITE.BSActivePW` | Battery/storage active power | int/float | `kW` | Sign convention unresolved |
| `PUB_SITE.Soc` | Site battery state of charge | int | `%` or unitless metadata | Percentage candidate |
| `BS.Soc` | Battery state of charge | int | `%` or unitless metadata | Percentage candidate |
| `BS.ChargingEngDay` | Battery charge energy today | float | `kWh` | Daily value, not cumulative |
| `BS.DischargingEngDay` | Battery discharge energy today | float | `kWh` | Daily value, not cumulative |
| `METER.APConsumed` | Meter consumed active energy | float | `kWh` | Need cumulative/reset evidence |
| `METER.APProduction` | Meter produced/exported active energy | float | `kWh` | Need cumulative/reset evidence |
| `DeviceState` | Device state | int | none | Diagnostic/status |
| `INV.State` | Inverter state | int | none | Diagnostic/status |
| `BS.State` | Battery state | int | none | Diagnostic/status |
| `OperatingStatus` | Site operating status | int | none | Diagnostic/status |
| `OperationState` | Site operation state | int | none | Diagnostic/status |

Observed metric fields:

| Field | Type | Unit | Period | Notes |
| --- | --- | --- | --- | --- |
| `ActiveProduction:TD` | float | likely `kWh` | today | Daily production |
| `ActiveProduction:MTD` | float | likely `kWh` | month to date | Period aggregate |
| `ActiveProduction:YTD` | float | likely `kWh` | year to date | Period aggregate |
| `ActiveProduction:BOL` | float | likely `kWh` | beginning of life | Candidate lifetime cumulative, needs confirmation |
| `SelfConsProduction:TD` | float | likely `kWh` | today | Daily self-consumed production |
| `OnGridIncome:TD` | float | currency | today | Financial, not energy |
| `Revenue:TD` | float | currency | today | Financial, not energy |

## Telemetry Sign Conventions

Sign conventions are partially proven by capture 3 and the sanitized human
notes. During the relevant capture window, the site was producing solar, the
house was consuming, the grid was exporting, and the battery was idle.

- `PUB_SITE.PVOutputPower`, `SITE.GenActivePW`, and `INV.GenActivePW` appear to
  represent positive generation power.
- `ConsPower` appears to represent positive household/load consumption.
- `PUB_SITE.METERActivePW` and `METER.ActivePW` represent grid/meter active
  power. In capture 3, the human note says the site was exporting to grid, and
  both fields were negative in all sampled live values. Therefore:
  - negative meter active power means grid export
  - positive meter active power likely means grid import, but should still be
    verified with an import-state capture
- `PUB_SITE.BSActivePW` and `BS.ActivePW` were zero while the human note says
  the battery was idle. This confirms zero means idle/no active battery power,
  but does not prove whether positive means charging or discharging.
- Dashboard-derived `ChargePower` was non-negative and `DischargePower` was
  non-positive in capture 3. The field names suggest positive charge power and
  negative discharge power, but live battery sign should still be verified with
  known charge and discharge captures.
- `METER.APConsumed` and `METER.APProduction` suggest import/export energy
  semantics, but monotonic behavior and reset behavior are not proven.

Additional capture evidence should include known grid import plus known battery
charge and battery discharge states to finish sign verification.

## Timestamp Formats, Time Zones, And Date Parameters

Observed telemetry point shape:

```json
{
  "timestamp": 1767222245000,
  "localtime": "2026-01-02 03:04:05",
  "value": 4.2,
  "attributes": {}
}
```

- `timestamp` appears to be Unix epoch milliseconds.
- `localtime` appears as `YYYY-MM-DD HH:MM:SS`.
- Site/device metadata includes a `timezone` field; observed shape is an IANA
  timezone string such as `Australia/Perth`.
- Some web endpoints use query parameter `timestemp=<EPOCH_MS>`; spelling is
  observed as `timestemp`.
- The captured time-series requests did not expose enough date range parameters
  to document historical range querying completely.

## Observed Polling Frequency

During an active portal session:

- `POST /<APP_ID>/monitor/v1.0/asset/list` repeats roughly every 30 seconds.
- `POST /<APP_ID>/monitor/v1.0/asset/detail` repeats roughly every 30 seconds.
- `POST /<APP_ID>/alarm/v1.0/alarmList` repeats roughly every 30 seconds.
- `POST /<APP_ID>/monitor/v1.0/measurement-point/time-series` appears when
  chart/history pages are opened, not as part of the normal live polling loop.
- `POST /<APP_ID>/datasource/v2/data/query` appears when dashboard/chart pages
  request widget batches, not as the core live polling loop.
- Metadata and bootstrap calls occur at login/session start and are not part of
  the regular telemetry poll loop.

For Home Assistant, a conservative initial scan interval should be no faster
than the portal's observed 30-second cadence. A longer interval such as 60 to
300 seconds may be more appropriate until rate limits are understood.

## Candidate Home Assistant Entities

Energy Dashboard suitability is marked "confirmed" only when live validation
has distinguished a lifetime counter from daily or interval values.

### Instantaneous Power In kW

| Candidate entity | Source field | HA class | Suitability |
| --- | --- | --- | --- |
| Solar power | `PUB_SITE.PVOutputPower` | `power`, `kW`, measurement | Good live sensor |
| Site/inverter power | `SITE.GenActivePW` or `INV.GenActivePW` | `power`, `kW`, measurement | Good live sensor; choose one canonical source |
| Household/load power | `ConsPower` | `power`, `kW`, measurement | Good live sensor |
| Grid power | `PUB_SITE.METERActivePW` or `METER.ActivePW` | `power`, `kW`, measurement | Positive import, negative export |
| Battery power | `PUB_SITE.BSActivePW` or `BS.ActivePW` | `power`, `kW`, measurement | Positive charging, negative discharging |
| Battery charge power | `ChargePower` | `power`, `kW`, measurement | Dashboard/chart field; non-negative charge candidate |
| Battery discharge power | `DischargePower` | `power`, `kW`, measurement | Dashboard/chart field; non-positive discharge candidate |

### Daily Energy In kWh

| Candidate entity | Source field | HA class | Energy Dashboard |
| --- | --- | --- | --- |
| Battery charge today | `BS.ChargingEngDay` | `energy`, `kWh` | Not confirmed; daily reset |
| Battery discharge today | `BS.DischargingEngDay` | `energy`, `kWh` | Not confirmed; daily reset |
| Grid import today | `METER.APConsumed` | `energy`, `kWh`, total | Daily reset; not an Energy Dashboard lifetime source |
| Grid export today | `METER.APProduction` | `energy`, `kWh`, total | Daily reset; not an Energy Dashboard lifetime source |
| Solar production today | `ActiveProduction:TD` | `energy`, `kWh` | Not confirmed; daily reset |
| Solar production today | `TotalActiveProduction:TD` | `energy`, `kWh` | Not confirmed; daily reset |
| Storage charge today | `StorageChargeProduction:TD` | `energy`, `kWh` | Not confirmed; daily reset |
| Storage discharge today | `StorageDischargeProduction:TD` | `energy`, `kWh` | Not confirmed; daily reset |
| Self-consumed solar today | `SelfConsProduction:TD` | `energy`, `kWh` | Not confirmed; daily reset |

Daily energy values may be useful regular sensors, but should not be exposed as
Energy Dashboard cumulative sources unless reset handling and Home Assistant
statistics behavior are deliberately implemented and tested.

### Lifetime Or Cumulative Energy In kWh

| Candidate entity | Source field | HA class | Energy Dashboard |
| --- | --- | --- | --- |
| Lifetime solar production | `ActiveProduction:BOL` | `energy`, `kWh`, total_increasing | Fallback source |
| Lifetime solar production | `TotalActiveProduction:BOL` | `energy`, `kWh`, total_increasing | Preferred source |
| Lifetime grid import | `METER.APConsumedKWH` | `energy`, `kWh`, total_increasing | Confirmed lifetime counter |
| Lifetime grid export | `METER.APProductionKWH` | `energy`, `kWh`, total_increasing | Confirmed lifetime counter |
| Lifetime battery charge | `BS.TotalChargingEng` | `energy`, `kWh`, total_increasing | Confirmed private-test source |
| Lifetime battery discharge | `BS.TotalDischargingEng` | `energy`, `kWh`, total_increasing | Confirmed private-test source |
| Lifetime storage charge | `StorageChargeProduction:BOL` or `BESSChargeEnergy:BOL` | `energy`, `kWh`, total_increasing candidate | Metadata candidate; still needs fetch/monotonic evidence |
| Lifetime storage discharge | `StorageDischargeProduction:BOL` or `BESSDischargeEnergy:BOL` | `energy`, `kWh`, total_increasing candidate | Metadata candidate; still needs fetch/monotonic evidence |

### Percentages

| Candidate entity | Source field | HA class |
| --- | --- | --- |
| Battery state of charge | `PUB_SITE.Soc` or `BS.Soc` | `battery`, `%`, measurement |

### Diagnostic And Status Values

| Candidate entity | Source field | Category |
| --- | --- | --- |
| Site operating status | `OperatingStatus` | diagnostic |
| Site operation state | `OperationState` | diagnostic |
| Device state | `DeviceState` | diagnostic |
| Inverter state | `INV.State` | diagnostic |
| Battery state | `BS.State` | diagnostic |

## Unrelated Or Unnecessary Endpoints

Likely unnecessary for a Home Assistant integration:

- `POST /<APP_ID>/alarm/v1.0/alarmList` unless alarm sensors are added later.
- `POST /<APP_ID>/web/v1/event/log/produce`, likely browser event logging.
- `GET /<APP_ID>/file/v1.0/site/graph`, likely portal visualization support.
- `GET /<APP_ID>/monitor/v1.0/<RESOURCE>` weather endpoint, unless weather
  sensors are explicitly desired.
- `POST /<APP_ID>/common/v1.0/dimension/list`, likely UI reference data.
- `GET /<APP_ID>/common/v1.0/config/read-lion` and
  `POST /<APP_ID>/web/v1/lion/spec/get`, likely UI configuration.
- `POST /<APP_ID>/open/dtm/<RESOURCE>`, purpose unclear from captures and not
  required for initial energy telemetry.

## Diagnostics Redaction Requirements

Diagnostics must redact at least:

- Passwords, account names, email addresses, phone numbers
- Tokens, session IDs, `_sid_`, refresh-token markers, cookies
- User IDs, organization IDs, company IDs
- Site IDs, device IDs, model paths, MDM paths
- Serial numbers and NMI values
- Address, latitude, longitude, contact fields
- Raw request and response payloads unless deeply sanitized

## Evidence Gaps Requiring Another Capture

Remaining evidence gaps before a polished Energy Dashboard integration:

1. How `_sid_` is produced after successful login:
   browser storage, JavaScript state, response side effect, or deterministic
   client-side generation. The first observed use is now known, but creation is
   not.
2. Whether login failure returns a useful JSON body, code, message, or HTTP
   status for invalid credentials.
3. The application-level response for expired or unauthenticated sessions.
4. Monotonic evidence across longer periods and restarts for non-shipped
   storage `BOL` metric candidates.
5. Whether multiple sites under one account are represented and how site
   selection should work in the config flow.
6. Rate limits, lockout behavior, and safe polling cadence.
7. Whether the `datasource/v2/data/query` endpoint is required for any values
   that cannot be fetched through simpler monitor endpoints.

Evidence now sufficient for a first read-only integration:

- Login can be attempted with the observed login endpoint and form shape, but
  `_sid_` creation remains the riskiest unknown.
- Discovery, metadata, live polling, and direct chart/history endpoints are now
  sufficiently mapped for an experimental read-only implementation.
- Live power, battery percentage, diagnostic sensors, and validated lifetime
  Energy Dashboard entities are sufficiently mapped for the current read-only
  integration.

Recommended minimum additional browser capture:

- Start with all site tabs closed and logged out.
- Open developer tools with "Preserve log" enabled.
- Log in with intentionally incorrect credentials once, then clear the network
  log.
- Log in with correct credentials.
- Capture from the login request through the first successful dashboard load.
- Keep recording for at least two live polling intervals.
- While recording, note real-world operating state separately, without putting
  private values in the repo: grid importing and battery charging/discharging
  are the highest-value missing states.
- Navigate to a chart/history view that shows lifetime/cumulative energy fields
  twice, separated by enough time to observe monotonic behavior.
- Export the HAR to `private/` only.
