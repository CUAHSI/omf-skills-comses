# HydroShare metadata collection and CodeMeta mapping

## Problem Statement

People assessing model software in HydroShare need repeatable metadata
collection and CodeMeta mapping without generating new extraction or conversion
code during each assessment. Resource-level metadata and aggregation-level
metadata describe different subjects, but both can contribute to a useful
aggregation CodeMeta record.

The current assessment process separates these scopes but does not provide the
maintained collector and mapper needed to apply the agreed enrichment rules
consistently. Uncontrolled merging can assign resource-wide facts to individual
models, obscure missing aggregation metadata, or misrepresent parent identifiers
as model identifiers.

## Solution

Provide maintained, reusable collection and mapping commands. Collect complete
resource-level metadata and aggregation-level metadata through anonymous,
read-only hsclient access, preserving the scopes in a saved source snapshot.
Map that snapshot without additional network access.

Produce a standalone resource CodeMeta record and one enriched aggregation
CodeMeta record for each ModelProgram or ModelInstance aggregation. Use explicit
field-specific rules to combine metadata, retaining field-level provenance and
unmapped source metadata. Report collection failures separately from legitimately
blank optional fields.

## User Stories

1. As an assessor, I want maintained collection commands, so that I do not need
   newly generated extraction code for every assessment.
2. As an assessor, I want to supply a HydroShare resource identifier, so that I
   can repeat the same workflow for different resources.
3. As an assessor, I want anonymous, read-only collection through hsclient, so
   that assessment neither requires credentials nor modifies HydroShare.
4. As an assessor, I want resource-level metadata collected separately from
   aggregation-level metadata, so that I can distinguish their subjects.
5. As an assessor, I want aggregation types inventoried, so that I can see which
   aggregations qualify for software assessment.
6. As an assessor, I want complete source metadata and file listings preserved,
   so that unmapped evidence remains available for inspection.
7. As an assessor, I want mapping to operate on a saved snapshot, so that I can
   revise or repeat mapping without collecting metadata again.
8. As an assessor, I want a standalone resource CodeMeta record, so that the
   resource remains separately represented.
9. As an assessor, I want one CodeMeta record per qualifying aggregation, so that
   individual models are represented independently.
10. As an assessor, I want multiple physical files in an aggregation to remain
    one metadata subject, so that file counts do not inflate model record counts.
11. As an assessor, I want only ModelProgram and ModelInstance aggregations to
    receive aggregation CodeMeta records, so that unrelated data aggregations
    are not represented as model software.
12. As a reviewer, I want each mapped value traced to its source scope and field,
    so that I can distinguish direct declarations from inherited values.
13. As an assessor, I want parent creators inherited as authors when direct
    aggregation authors are absent, so that parent authorship information is
    available without concealing its origin.
14. As a reviewer, I want inherited creators to retain their listed order, so
    that conversion does not silently change attribution order.
15. As an assessor, I want aggregation rights to take precedence, so that a
    parent license does not overwrite an aggregation-specific declaration.
16. As an assessor, I want parent rights used when aggregation rights are absent,
    so that the approved license fallback is applied consistently.
17. As an assessor, I want an explicit aggregation title preserved even if
    generic, so that conversion does not silently rewrite source metadata.
18. As an assessor, I want the parent title used only when an aggregation title
    is absent, so that the fallback remains limited and traceable.
19. As an assessor, I want a provisional parent-abstract fallback when an
    aggregation description is absent, so that the agreed interim behavior is
    available while its suitability remains open for review.
20. As a reviewer, I want description inheritance visibly marked as provisional,
    so that it is revisited rather than treated as settled methodology.
21. As an assessor, I want keywords drawn only from aggregation subjects, so that
    resource-wide topics are not silently assigned to every model.
22. As an assessor, I want aggregation URLs used as aggregation identifiers, so
    that models in the same resource remain distinguishable.
23. As a reviewer, I want parent identifiers and DOIs kept separate, so that they
    are not misrepresented as identifiers assigned to an aggregation.
24. As an assessor, I want explicit aggregation release dates mapped to
    datePublished, so that resource publication is not confused with software
    release.
25. As an assessor, I want technical fields mapped only from explicit aggregation
    metadata, so that repository URLs, versions, languages, and operating systems
    are not guessed.
26. As an assessor, I want explicit ModelInstance execution relationships
    preserved as softwareRequirements, so that dependencies remain traceable.
27. As an assessor, I want inherited values to count as present with disclosure,
    so that enrichment is useful without hiding aggregation-level omissions.
28. As an assessor, I want empty optional fields distinguished from collection
    errors, so that missing metadata does not unnecessarily stop conversion.
29. As an assessor, I want collection errors to block mapping for that run, so
    that incomplete collection cannot appear to be a complete assessment.
30. As a reviewer, I want partial evidence and explicit errors preserved, so that
    failed collection can be investigated.
31. As a maintainer, I want offline regression fixtures, so that mapping changes
    can be tested without depending on HydroShare availability.
32. As a maintainer, I want a separate read-only integration check with collection
    time and library versions recorded, so that live observations are
    reproducible within their stated conditions.
33. As a maintainer, I want the assessment instructions aligned with the maintained
    commands, so that agents do not revert to ad hoc code generation.

## Implementation Decisions

- Keep the change centered on the HydroShare assessment workflow and directly
  related FAIR guidance, assets, and deterministic automation.
- Provide separate maintained collector and mapper commands with public
  command-line interfaces. The collector accepts a resource identifier; the
  mapper accepts a saved source snapshot. Agents run maintained code unchanged
  rather than generating or patching assessment-specific Python.
- Use public hsclient interfaces for resource metadata, system metadata,
  aggregation metadata, and file listings. Record collection time and installed
  hsclient and hsmodels versions.
- Keep collection anonymous, read-only, and metadata-only. Do not download model
  contents, scrape landing pages, substitute hand-written REST calls, prompt for
  authentication, or invoke HydroShare write operations.
- Preserve complete collected resource metadata and in-scope aggregation
  metadata in separate snapshot sections. Inventory other aggregation types
  without generating software CodeMeta records for them.
- Preserve the existing no-qualifying-aggregation scope gate: report the observed
  types and counts and stop software assessment when neither ModelProgram nor
  ModelInstance is present.
- For an in-scope resource with N qualifying aggregations, produce N aggregation
  CodeMeta records plus one standalone resource CodeMeta record. Do not produce
  one record per physical file.
- Keep standalone resource mapping separate from aggregation enrichment.
  Parent-to-aggregation rules below do not redefine the standalone resource
  record's mapping.
- Use a companion mapping report to identify the source scope, source field,
  and rule for each mapped value, including inherited and inferred mappings.
  Preserve unmapped fields in the source snapshot instead of inventing CodeMeta
  properties.
- Prefer explicit aggregation values over parent fallbacks. Parent inheritance
  is an allowlist, not a general merge:
  - Authors: inherit parent creators when direct aggregation authors are absent,
    preserve order, and label the source as inherited.
  - License: use aggregation rights when supplied; otherwise inherit parent
    rights and record the fallback.
  - Name: preserve the aggregation title, including generic titles; inherit the
    parent title only when the aggregation title is absent. Report a generic
    title as a quality issue rather than renaming it.
  - Description: provisionally use the parent abstract when no aggregation
    description exists. Direct aggregation descriptions take precedence.
    Disclose inheritance and the provisional policy status.
- Use only aggregation subjects for keywords. Neither merge parent subjects nor
  fall back to them when aggregation subjects are empty.
- Use the aggregation URL as its identifier. Do not assign the parent's
  identifier or DOI to the aggregation.
- Map the aggregation release date to datePublished without a parent publication
  date fallback.
- Use only explicit aggregation metadata for version, codeRepository, website,
  programmingLanguage, and operatingSystem. Do not infer values from names,
  filenames, repository URLs, or parent metadata.
- Map an explicit ModelInstance execution relationship to softwareRequirements,
  recording its source and mapping rationale. Do not infer a relationship from
  names or co-location.
- Do not infer software maintainership from resource ownership or software
  creation/modification dates from resource creation/modification dates.
- Count inherited values as present in presence checks while distinguishing
  inherited values from directly declared aggregation metadata in findings.
- Treat blank, null, empty, and absent optional metadata as missing evidence,
  not collection failures. Do not invent replacement values.
- On collection failures, preserve partial evidence, identify the failed scope
  and error, mark collection incomplete, and return an explicit unsuccessful
  outcome. Block mapping of that run rather than issuing apparently complete
  CodeMeta output. Access denial and unparseable responses are collection
  failures, not blank metadata.
- Update directly related workflow instructions and evaluation coverage for the
  changed behavior. Follow the existing skill stewardship contract when
  behavior-affecting skill content changes; structural checks are not evidence
  of scientific correctness.

## Testing Decisions

- The user confirmed one workflow-level testing seam: invoke the maintained
  scripts through their public command-line interfaces and inspect externally
  visible outputs and exit status. Use offline hsclient-boundary fixtures rather
  than testing private functions or internal call sequences.
- Test collection and mapping as a workflow, including mapping a saved snapshot
  without network access. Verify source snapshot content, exact CodeMeta record
  counts and subjects, mapping provenance, incomplete-collection handling, and
  explicit unsuccessful outcomes.
- Use separate resource and aggregation fixtures to establish field origin.
  The user-supplied combined SUMMA JSON is a regression example, not proof of
  which scope originally supplied each field.
- Cover a resource with multiple qualifying aggregations, an aggregation
  containing several physical files, mixed qualifying and non-qualifying types,
  and the existing no-qualifying-aggregation gate.
- Verify direct aggregation values, each allowed fallback, conflicts, creator
  order, generic titles, and the absence of unapproved parent fallbacks.
- Assert that empty aggregation subjects do not inherit parent keywords,
  parent DOIs do not become aggregation identifiers, and parent publication
  dates do not replace missing aggregation release dates.
- Verify the explicit ModelInstance execution mapping and the absence of guessed
  relationships.
- Verify that inherited fields satisfy presence checks while findings disclose
  their origin, including the provisional description policy.
- Test blank optional fields separately from access, request, and parsing
  failures. Verify that partial snapshots remain available but incomplete runs
  cannot generate apparently complete mapped output.
- Use the SUMMA example to check explicit title, version 2.0.0, release date
  2017-05-30, repository, website, rights, creator order, and empty language and
  operating-system lists.
- Existing repository validation covers skill/evaluation schemas, provenance,
  stewardship, and cross-skill contracts. Reuse that validation infrastructure,
  but do not treat structural checks as a substitute for the new workflow
  regression tests. Wire offline regression tests into the documented make
  workflow without requiring live HydroShare access.
- Keep the live read-only integration check separate from routine offline tests.
  Record resource identifier, collection time, library versions, observed
  results, and limitations. Do not treat changing remote metadata as immutable
  fixture truth.
- Run the canonical make validate command before considering implementation
  complete. Report environment blockers explicitly.

## Out of Scope

- Implementing the feature as part of specification authoring.
- HydroShare metadata edits, uploads, or authenticated/private-resource support.
- Downloading, executing, or inspecting model contents to fill metadata gaps.
- CodeMeta records for individual physical files or non-model aggregations.
- Automatic inference of authorship, technical fields, or dependencies beyond
  the approved mapping rules.
- Arbitrary parent-to-aggregation metadata merging.
- Invented CodeMeta properties for unmapped HydroShare metadata.
- Broad redesign of FAIR assessment, upstream converters, or unrelated skills.
- Settling the scientific appropriateness of description inheritance in this
  implementation; that requires the explicitly requested future discussion.

## Further Notes

- The design was confirmed on 2026-10-26. Confirmation closed the interview;
  specification authoring does not itself implement the design.
- Description inheritance remains provisional. Revisit whether the parent
  abstract describes each aggregation accurately, especially for resources
  containing multiple models. Do not present the interim choice as a settled
  methodological recommendation.
- The reference resource is
  <https://www.hydroshare.org/resource/5d5da76611d64b7a8105fadbc5ac7828/>.
  The user supplied a combined metadata example; this specification does not
  claim a fresh live collection was performed.
- The intended issue tracker is GitHub Issues for CUAHSI/omf-skills-comses.
  The ready-for-agent triage label was created, and this specification was
  published as issue #3 on 2026-10-26 after an initial attempt was blocked
  because Issues was disabled.
- An earlier make validate attempt could not start containerized checks because
  the Docker Desktop Linux engine was unavailable. No passing validation or live
  integration result is claimed.
