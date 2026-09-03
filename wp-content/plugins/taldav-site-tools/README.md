# TalDav Site Tools

Small site-specific WordPress plugin for the TalDav / WP Care portfolio website.

## What It Does

- Provides the `[taldav_support_calculator]` shortcode.
- Adds a configurable WordPress support calculator.
- Lets the site owner edit calculator texts.
- Lets the site owner add, remove and edit calculator services.
- Supports a configurable discount rule.
- Writes calculator output into configured form fields by `name` attribute.
- Keeps custom JavaScript and CSS outside of the WordPress Customizer.
- Makes site-specific code visible in WordPress admin under Plugins.

## Admin Settings

Open:

```text
Settings -> TalDav Site Tools
```

The settings page is split into two areas:

- main content: calculator texts and service rows;
- right sidebar: discount, currency and form integration.

Available settings:

- open button text;
- modal top label;
- modal title;
- modal description;
- total label;
- apply button text;
- currency symbol;
- discount enabled/disabled;
- discount threshold;
- discount percent;
- optional form CSS selector;
- target field name for the estimated price;
- target field name for selected services;
- dynamic service list.

## Form Integration

By default the calculator writes to fields with these `name` attributes:

```text
estimated_monthly_price
selected_custom_services
```

The integration is not tied to Fluent Forms directly. It uses field `name` attributes, so it can work with different form plugins.

If a page has more than one form, set `Optional Form CSS Selector`, for example:

```text
.fluent_form_5
```

## Shortcode

Add this shortcode to the Pricing page where the calculator button should appear:

```text
[taldav_support_calculator]
```

The same calculator can also be opened by a custom button or link that uses one of these selectors:

```html
<a href=#support-calculator>Estimate Support</a>
<button class=taldav-open-calculator>Estimate Support</button>
```

The current Fluent Forms button with ID `wp-care-open-calculator` is also supported.
