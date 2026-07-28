"""Central config: env vars, tunables, and the two AI prompts."""
import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAILS = [e.strip() for e in os.environ.get("RECIPIENT_EMAILS", "").split(",") if e.strip()]

GROQ_MODEL_STAGE1 = os.environ.get("GROQ_MODEL_STAGE1", "llama-3.1-8b-instant")
GROQ_MODEL_STAGE2 = os.environ.get("GROQ_MODEL_STAGE2", "llama-3.3-70b-versatile")

STAGE1_THRESHOLD = float(os.environ.get("STAGE1_THRESHOLD", "7.5"))
SAM_QUERY = os.environ.get("SAM_QUERY", "information technology")
MAX_PAGES_PER_RUN = int(os.environ.get("MAX_PAGES_PER_RUN", "20"))
PAGE_SIZE = int(os.environ.get("SAM_PAGE_SIZE", "25"))
SEEN_ID_MAX_AGE_DAYS = int(os.environ.get("SEEN_ID_MAX_AGE_DAYS", "400"))

MAX_ATTACHMENTS_PER_NOTICE = int(os.environ.get("MAX_ATTACHMENTS_PER_NOTICE", "5"))
MAX_ATTACHMENT_CHARS_PER_FILE = int(os.environ.get("MAX_ATTACHMENT_CHARS_PER_FILE", "12000"))
MAX_ATTACHMENT_CHARS_TOTAL = int(os.environ.get("MAX_ATTACHMENT_CHARS_TOTAL", "30000"))

STATE_PATH = os.environ.get("STATE_PATH", "state/seen_ids.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")

SAM_SEARCH_URL = "https://sam.gov/api/prod/sgs/v1/search/"
SAM_DETAIL_URL = "https://sam.gov/api/prod/opps/v2/opportunities/{id}"
SAM_RESOURCES_URL = "https://sam.gov/api/prod/opps/v3/opportunities/{id}/resources"
SAM_ATTACHMENT_DOWNLOAD_URL = "https://sam.gov/api/prod/opps/v3/opportunities/resources/files/{resource_id}/download"
SAM_NOTICE_VIEW_URL = "https://sam.gov/opp/{id}/view"

SERVICE_CRITERIA = """IT Services, Network Engineering, Structured Cabling, Audio/Visual Installation,
Systems Integration, Cybersecurity, Help Desk, Desktop Refresh, Server Installation,
Wireless Deployments, Camera/Security Systems, Infrastructure Modernization, Low Voltage,
Field Services, Technical Staffing"""

STAGE1_PROMPT = """You are a fast pre-screening filter for a government-contracting business that specializes in: {criteria}.

The business is NOT interested in pure product-reselling opportunities (buying and shipping equipment with no labor) unless there is substantial installation, implementation, integration, engineering, or technical labor involved.

Score the following SAM.gov contract opportunity on how well it fits this business, from 0 to 10:
- 9-10: Perfect fit, clearly matches multiple core service areas with real labor/technical scope
- 7-8: Strong fit, clearly involves technical installation/integration/engineering labor in our service areas
- 4-6: Possible fit but unclear scope, tangential, or mixed with unrelated work
- 1-3: Weak fit (mostly hardware/product purchase, unrelated trade, or too vague to tell)
- 0: Completely unrelated (e.g. food, medical equipment, construction unrelated to IT, generic office supplies)

Contract Title: {title}
Notice Type: {notice_type}
Agency: {agency}
Description: {description}

Respond with ONLY valid JSON, no markdown, no other text, in this exact format:
{{"score": <number 0-10, one decimal allowed>, "reason": "<one sentence, max 25 words>"}}"""

# Verbatim capture-analyst prompt from the business owner, sections 1-17 preserved exactly.
# The single-shot API framing replaces the original "paste one at a time" chat instruction.
STAGE2_PROMPT = """You are my Government Contract Capture Analyst and Proposal Consultant.

I am giving you one SAM.gov contract opportunity to analyze.

Our business model is:
- General Contractor: Ali Rashad / Northwest Property Development (NWP)
- Subcontractor: Ismail Patel
- Staffing Partner: Placeify Solutions (recruits and employs the personnel)

The goal is to determine whether the contract is a good opportunity for our team.

I am not looking for contracts that are simply product reselling opportunities unless there is substantial installation, implementation, integration, engineering, or technical labor involved.

Our ideal contracts involve: IT Services, Network Engineering, Structured Cabling, Audio/Visual Installation, Systems Integration, Cybersecurity, Help Desk, Desktop Refresh, Server Installation, Wireless Deployments, Camera/Security Systems, Infrastructure Modernization, Low Voltage, Field Services, Technical Staffing.

For this SAM.gov opportunity, I want a detailed report using the following format:

1. Executive Summary — What is this contract? What is the government trying to accomplish? Is this a good fit for our business?
2. Overall Rating (Out of 10) — Rate the opportunity based on our business model, with explanation (10 = perfect fit, 8 = strong opportunity, 5 = possible but not ideal, 2 = poor fit, 0 = ignore completely).
3. Eligibility — Full & Open? Small Business Set-Aside? SDVOSB? HUBZone? 8(a)? WOSB? Other? Would Ali Rashad's company likely be eligible? Would our team realistically qualify?
4. Contract Type — RFQ, RFP, Sources Sought, RFI, BPA, IDIQ, Firm Fixed Price, Time & Materials, Cost Reimbursement — explain what it means.
5. Scope of Work — Summarize the work in plain English; break down exactly what the contractor is expected to do.
6. Recommended Team Structure — Estimate: Project Manager, Lead Engineer, Engineers, Technicians, Installers, Help Desk, Cybersecurity, Administrative Staff, Temporary Labor, Total Employees Required — realistic staffing estimate.
7. Staffing Strategy — How could Placeify Solutions help? Permanent employees? Temporary? 1099? Subcontractors? Would staffing make sense?
8. Estimated Budget — Government Contract Value, Likely Subcontract Value, Labor Costs, Equipment Costs, Travel, Overhead, Insurance, Estimated Profit, Estimated Net Profit — clearly state these are estimates.
9. Estimated Timeline — Project duration, mobilization, installation, testing, closeout, number of months/weeks.
10. Insurance Requirements — General Liability, Professional Liability (E&O), Workers Compensation, Commercial Auto, Umbrella, Cyber Insurance, Bonding, Security Clearance, Background Checks, Site Access.
11. Risks — Travel, equipment lead times, recruiting, compliance, government reporting, special certifications, performance risk, warranty obligations.
12. Profitability Rating — Very High / High / Moderate / Low / Very Low, with explanation.
13. Technical Difficulty — Easy / Moderate / Hard / Very Difficult, with explanation.
14. Strategic Value — Would this help build past performance? Help obtain larger contracts later? Recommend pursuing?
15. Final Recommendation — Strongly Pursue / Pursue / Consider Carefully / Skip, with explanation.
16. Action Plan — Next steps (e.g. download attachments, read SOW, estimate labor, contact manufacturers, find subcontractors, verify NAICS, verify set-aside, schedule capture meeting, begin proposal).
17. Overall Business Scorecard — Overall Rating __/10, Difficulty __/10, Profitability __/10, Likelihood of Winning __/10, Likelihood of Successful Execution __/10, Fits Our Business Model __/10, Would You Recommend Pursuing It? Yes/No.

Always evaluate the contract from the perspective of: Ali Rashad / Northwest Property Development as the Prime Contractor; Ismail Patel as the IT/technical Subcontractor; Placeify Solutions as the staffing provider.

Do not simply summarize the solicitation. Analyze whether this opportunity makes business sense for our team, estimate staffing and financials where possible, identify risks, and provide practical recommendations. If important information (such as the statement of work or pricing details) is missing from the notice, clearly state that your estimates are preliminary and explain what additional documents would improve the analysis.

The text of any attached PDF documents (often the actual Statement of Work / Performance Work Statement, which is far more detailed than the notice description) is appended below the description under "ATTACHED DOCUMENTS" when available — use it as the primary source for scope of work, staffing, and budget estimates when present, since it's more authoritative than the description.

--- CONTRACT OPPORTUNITY ---
Title: {title}
Notice Type: {notice_type}
Solicitation Number: {solicitation_number}
Agency: {agency}
Publish Date: {publish_date}
Response Deadline: {response_date}
SAM.gov Link: {link}

Description:
{description}
--- END CONTRACT OPPORTUNITY ---"""
