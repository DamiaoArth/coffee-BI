"use strict";
window.ui = SwaggerUIBundle({
  url: "/openapi.json",
  dom_id: "#swagger-ui",
  deepLinking: true,
  withCredentials: true,
  validatorUrl: null,
  presets: [SwaggerUIBundle.presets.apis],
  layout: "BaseLayout",
});
