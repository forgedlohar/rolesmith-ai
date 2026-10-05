# Configuration

Rolesmith AI requires you to set up your profile and credentials in `~/.rolesmith/config.json`.

## Generating the Template

To generate the configuration template, run:
```bash
uv run rolesmith-ai init
```
This will initialize your configuration in `~/.rolesmith/config.json` with a comprehensive `candidate_profile` block.

## Profile Structure

Fill in your details meticulously:
- `personal_info`: Name, email, phone, location.
- `education`: Degrees and universities.
- `experience`: A list of past roles. For each, include `company`, `title`, `dates`, and a robust list of `bullets`.
- `skills`: Categorized skills (languages, frameworks, tools).

Rolesmith uses this data to tailor your resume and answer dynamic form questions correctly.

## PDF Resume Generation

Rolesmith compiles LaTeX files to generate tailored PDF resumes. You must place your master LaTeX template in:
`~/.rolesmith/resume_template.tex`

The pipeline uses `pdflatex` to render the customized resume on the fly.
