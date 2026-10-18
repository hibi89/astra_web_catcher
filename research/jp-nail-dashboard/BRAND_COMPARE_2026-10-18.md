# Brand compare UI observation — 2026-10-18

Source: user's browser, read-only text snapshot after one click. Current URL fragment: `#v-brand`; menu title: 브랜드 비교. Previous: `#v-tags`, tag filter 컬러 8 rows.

Observed unchanged state: NAILTOWN side panel (4-week index 1.26), analyzed 49, collected 61, average response 217, Reels 9, report #3728.

Brand comparison data present in page text:

| Brand | Analyzed | Response median | 4-week index |
|---|---:|---:|---:|
| NAILTOWN | 49 | 143 | 1.26 |
| GELME1 | 22 | 245 | 1.00 |
| OHORA | 79 | 223 | 0.91 |
| EDGEU | 3 | 2 | not shown |

The page text still contains the 8 color tags. **Unknown** whether those rows/brand comparison tables and charts are visible on this screen, because the read-only page extractor may include hidden sections. Need one screenshot of current brand comparison view before inferring layout or interactions.

No source/API/network access, no app implementation, no changes to main or previous MVP tests.

## User screenshot confirms visible brand comparison layout

- Evidence: user-provided screenshot, uploaded in this conversation as `image(20261018-081243).png` (not copied to GitHub because browser screenshots may contain unrelated personal tab information). Screen address shows `#v-brand`.
- **Visible view:** left navigation `브랜드 비교` selected. Main panel has exactly **two horizontal-bar chart cards in first row**: (A) `브랜드별 반응 중앙값`; (B) `브랜드별 4주 성과지수`. Underneath is the `브랜드 상세` table with four brands and seven fields. Top central content lacks the tag-category filters and the dashboard's five-brand selector bar in this screenshot.
- **Right panel:** NAILTOWN purple circle/avatar and index `1.26` persist. This indicates the selected side-panel context stays NAILTOWN while the comparison cards simultaneously display **all four brands**. Do NOT mistakenly filter comparison results to only the side-selected brand.
- **Chart A data (visible):** NAILTOWN 143 (followers 133,519), GELME1 245 (55,279), OHORA 223 (163,947), EDGEU 2 (6,429). Horizontal bars carry brand colors. Legend states `막대 = 게시물 반응 중앙값`.
- **Chart B data (visible):** NAILTOWN 1.26 (recent 4wk posts 16), GELME1 1.00 (5), OHORA 0.91 (40), EDGEU index absent (recent 4wk 0). Label states `1 = 브랜드 평소 수준`; absent EDGEU index is **null/missing**, not a verified numeric zero.
- **Visible detail columns:** 브랜드; 구분; 팔로워; 분석 게시물; 최근 4주 게시; 반응 중앙값; 최근 4주 성과지수 중앙값; 조회수 확보율.

| 브랜드 | 구분 | 팔로워 | 분석 게시물 | 최근 4주 게시 | 반응 중앙값 | 4주 지수 | 조회수 확보율 |
|---|---|---:|---:|---:|---:|---:|---:|
| NAILTOWN | 셀프·직접 시술 | 133,519 | 49 | 16 | 143 | 1.26 | 14.75% |
| GELME1 | 셀프·직접 시술 | 55,279 | 22 | 5 | 245 | 1 | 38.89% |
| OHORA | 셀프·시트형 | 163,947 | 79 | 40 | 223 | 0.91 | 82.98% |
| EDGEU | 셀프·시트형 | 6,429 | 3 | 0 | 2 | — | 0% |

**Confirmed now:** two charts and full four-row table are ACTUALLY VISIBLE, correcting the prior uncertainty when only hidden+visible DOM text was available. This appears to be a cross-brand comparison page independent of the selected right-side brand context.

**Still unconfirmed:** whether bars/table are clickable or provide hover tips, data freshness, calculations, source API vs static JSON, persistence of the earlier `컬러` filter after returning to tag view, behavior at other screen sizes.

**Next single user action:** click `상위 게시물` in left menu once and reply `눌렀어`; re-read connected tab and compare URL, visible report text, list count and whether the right panel remains selected. Request a screenshot only if text extraction cannot prove visible layout or behaviors.
