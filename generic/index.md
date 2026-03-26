---
layout: default
title: Generic Documents
---

# Generic Documents

Generic documents record **what is generally true about things like this** -- universal judgments parameterized over a class of systems or situations. They reference external evidence and other generics, but not ground or hypothetical documents.

## Documents

<ul>
{% assign gen_pages = site.pages | where: "doc_kind", "generic" %}
{% for doc in gen_pages %}
  {% unless doc.url == "/generic/" %}
  <li class="doc-list-item">
    <a href="{{ doc.url | relative_url }}">{{ doc.title | default: doc.name }}</a>
    {% if doc.created %}<span class="doc-date">{{ doc.created }}</span>{% endif %}
  </li>
  {% endunless %}
{% endfor %}
</ul>
