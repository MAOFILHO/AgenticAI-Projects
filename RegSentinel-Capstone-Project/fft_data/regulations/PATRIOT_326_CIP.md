# Customer Identification Program (CIP)

**Citation:** USA PATRIOT Act § 326 / 31 CFR § 1020.220  
**Authority:** FinCEN / Treasury  

## Summary

Every bank must implement a written CIP to verify the identity of each customer opening an account.

## Key Requirements

- Collect name, date of birth (individuals), address, and identification number (SSN/TIN/EIN) before account opening.
- Verify identity within a reasonable time using documentary or non-documentary methods.
- Maintain identification records for five years after the account is closed.
- Screen customers against government lists where required.

## Detection Indicators

- Account opened without a completed CIP.
- KYC status 'failed' or 'pending' on an active, transacting account.
- Beneficial owner of a legal-entity customer not identified.

## Enforcement

Supervisory action, civil money penalties, and reputational/enforcement risk under BSA.

## Source

<https://www.ecfr.gov/current/title-31/subtitle-B/chapter-X/part-1020/subpart-B/section-1020.220>
