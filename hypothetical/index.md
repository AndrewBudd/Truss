---
layout: default
title: Hypothetical Documents
---

# Hypothetical Documents

Hypothetical documents record **what follows from what we know** -- conditional judgments that depend on ground truths and other documents via explicit `assumes:` references with pinned commit hashes.

## Documents

<ul>
{% assign hyp_pages = site.pages | where: "doc_kind", "hypothetical" %}
{% for doc in hyp_pages %}
  {% unless doc.url == "/hypothetical/" %}
  <li class="doc-list-item">
    <a href="{{ doc.url | relative_url }}">{{ doc.title | default: doc.name }}</a>
    {% if doc.created %}<span class="doc-date">{{ doc.created }}</span>{% endif %}
  </li>
  {% endunless %}
{% endfor %}
</ul>
