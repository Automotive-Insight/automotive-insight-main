# Blog

The blog is plain static HTML like the rest of the site. Pages in `/blog/` are
generated from the source files in `_blog/posts/` by `_blog/build.py`. The
`_blog/` folder is in `.assetsignore`, so it is never deployed.

## Add a post

1. Copy any file in `_blog/posts/` to `_blog/posts/<new-slug>.html`.
2. Edit the JSON block at the top:
   - `slug` must match the file name. It becomes `/blog/<slug>/`.
   - `title` is the H1. `metaTitle` is the `<title>` (keep it under ~60 characters).
   - `description` is the meta description (~150 characters).
   - `category` is the topic shown on the card and used by the filter. Use an
     existing one where you can (`European cars`, `Hybrid servicing`,
     `Buying guides`, `EV servicing`, `Fleet`, `Ownership`). Anything after a
     `|` shows in the post's kicker only, e.g. `Buying guides | Toyota`.
   - `tagline` is the hero subheading and the card excerpt.
   - `datePublished` / `dateModified` are `YYYY-MM-DD`. A post dated in the
     future is skipped until the build is run on or after that date.
   - `image` goes in `/img/blog/`, 1200×675 JPG. `imageAlt` describes it.
   - `related` lists up to three slugs; the build fills any gaps.
   - `visitLead` and `serviceLink` set the booking box text and its link.
3. Write the body as HTML below the JSON block. Start with an intro `<p>`, then
   the optional `<aside class="takeaways">` box, then `<h2>` sections.
4. Below `<!-- FAQ -->`, add `<h3>question</h3><p>answer</p>` pairs. They become
   the accordion and the FAQPage schema.
5. Below `<!-- SOURCES -->`, add a `<ul>` of source links (or leave it empty).
6. Run `python3 _blog/build.py` from the repo root, check the page locally,
   then commit the source file, the image and the generated `blog/` files
   together.

The build also refreshes the blog entries in the sitemap (inside
`_worker.js`, between the `BLOG-SITEMAP` markers) and in `llms.txt`. Don't edit
those blocks by hand.

## Change the design

- `templates/page.html` is the shared shell: head, tracking, booking modal,
  nav and footer, cut from the live inner pages. If the nav, footer, modal or
  tracking change on the rest of the site, make the same change here.
- `templates/blog.css` holds all blog styles.
- `templates/post-hero.html`, `post-main.html`, `index-hero.html`,
  `index-main.html` and `card.html` are the page sections.

Run the build after any template change so every post picks it up.

## House rules for post copy

Same as the rest of the site: Australian spelling, the main number
0482 097 182, 30+ years / since 1993, and no "specialist" or "every make"
claims about the workshop.
