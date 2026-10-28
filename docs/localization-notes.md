# Localization notes

These notes explain selected English-to-Japanese decisions in the fictional
Kotoha Cloud interface. They are examples of process and judgment, not claims
about work completed for a client.

| Key | English | Japanese | Rationale |
| --- | --- | --- | --- |
| `hero.title` | Ship words that feel at home. | 言葉を、その土地の空気へ。 | A literal shipping metaphor would sound mechanical. The Japanese line keeps the idea of language belonging naturally in its destination while remaining compact enough for a hero heading. |
| `workspace.status` | On track | 予定どおり | This is a project-status label, so the established concise expression is clearer than a literal reference to a “track.” |
| `review.greeting` | Welcome back, `{name}`. | おかえりなさい、`{name}`さん。 | The placeholder is preserved exactly. `さん` adds appropriate warmth for the fictional consumer-facing context. |
| `review.delivery` | Your order will arrive in `{count}` days. | 商品は`{count}`日後にお届け予定です。 | Japanese commonly omits the explicit second-person possessive. `お届け予定です` communicates an estimate without overpromising. |
| `review.total` | Total: `{amount}` | 合計：`{amount}` | The full-width colon follows Japanese UI typography while the amount placeholder remains unchanged. |

## Quality approach

Structural QA checks key parity, placeholders, empty values, invalid control
characters, and paired YAML structure. Conservative language heuristics flag
untranslated text and a few patterns that often benefit from editing. A flag is
a review prompt—not proof that a translation is wrong.

Machine translation and AI-assisted suggestions can accelerate drafting, but
they require review by a qualified human who understands the product context,
audience, terminology, and brand voice before publication.
