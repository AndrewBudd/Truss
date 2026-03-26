---
layout: default
title: Ground Documents
---

# Ground Documents

Ground documents record **what is the case** -- categorical judgments backed by external evidence such as URLs, files, or direct observations. They form the factual foundation of the knowledge base.

Ground documents do not have `assumes:` fields. They reference only external evidence.

## Documents

<ul>
{% assign ground_pages = site.pages | where: "doc_kind", "ground" %}
{% for doc in ground_pages %}
  {% unless doc.url == "/ground/" %}
  <li class="doc-list-item">
    <a href="{{ doc.url | relative_url }}">{{ doc.title | default: doc.name }}</a>
    {% if doc.created %}<span class="doc-date">{{ doc.created }}</span>{% endif %}
  </li>
  {% endunless %}
{% endfor %}
</ul>
