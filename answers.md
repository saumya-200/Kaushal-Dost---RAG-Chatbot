================================================================================
  UPSDM RAG CHATBOT - QUESTION BANK LATENCY & ACCURACY TEST
================================================================================
  Server: http://localhost:8000
  Ensure Docker containers are running (redis, ollama, brain).
  Total questions: 26
================================================================================
  Starting test in 3 seconds...

================================================================================
  PERSONA: STUDENT (8 questions)
================================================================================

  Q1. What is UPSDM?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          FAISS_DIRECT
  Client Latency: 212.61 ms
  Server Latency: 204.70 ms
  Source IDs:     www.upsdm.gov.in/Home/FAQ__chunk_000, www.upsdm.gov.in/Home/Downloads__chunk_005, www.upsdm.gov.in/Home/DSDP__chunk_008
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    UPSDM stands for Uttar Pradesh Skill Development Mission. It aims to train
    eligible youth aged 14-35 in preferred trades, upgrade skills of
    unskilled/semi-skilled workforce, and provide provisions for women, PWD,
    and minorities.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    According to official UPSDM guidelines from upsdm.gov.in/Home/FAQ: UPSDM
    FAQ: 1. What is UPSDM? UPSDM holds the distinction of being the pioneering
    state in India to attain this prestigious recognition." leads to
    /Content/WebAssets/pdfFiles/Awarding_Body_Banner.pdf - Link: "Training
    Partner Evaluation Details for FY 2017-18 & 2018-19" leads to
    /Content/WebAssets/pdfFiles/TPEvaluationSheet.pdf - Link: "Candidate
    Registration User Manual" leads to /Content/UserManual/Candidate
    Registration User Ma
  ────────────────────────────────────────────────────────────────────────────

  Q2. How can I enroll in a skill development course?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 59.06 ms
  Server Latency: 54.75 ms
  Source IDs:     www.upsdm.gov.in/Home/FAQ__chunk_007, www.upsdm.gov.in/Home/SkillMitraIndex__chunk_000, www.upsdm.gov.in/Home/NewDirection__chunk_003
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Candidates can register through the Kaushal Drishti portal or the
    Candidate Registration link on upsdm.gov.in. They need to visit a nearby
    Skill Development Center.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    To register for UPSDM skill development courses, visit upsdm.gov.in and
    click on 'Candidate Registration' in the navigation menu. You can also
    register through the Kaushal Drishti portal.
  ────────────────────────────────────────────────────────────────────────────

  Q3. What are the eligibility criteria for the PMKVY scheme?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          FAISS_DIRECT
  Client Latency: 737.76 ms
  Server Latency: 736.05 ms
  Source IDs:     www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_000, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_001, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_013
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Eligible youth in the 14-35 age group can enroll. Trainings are in
    NSQF-compliant courses only. 30% targets are earmarked for women and 20%
    for minorities.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    According to official UPSDM guidelines from
    upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf:
    Short Term Training Guidelines The Short Term Training imparted at PMKVY
    Training Centres (TCs) is expected to beneﬁt candidates of Indian
    nationality who are either school/college dropouts or unemployed. Special
    Projects are projects that require some deviation from the terms and
    conditions of Short Term Training under PMKVY for any stakeholder. For
    further clariﬁcation on
  ────────────────────────────────────────────────────────────────────────────

  Q4. Do you provide placement assistance after training?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 37.64 ms
  Server Latency: 33.70 ms
  Source IDs:     www.upsdm.gov.in/Home/FAQ__chunk_008, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_007, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_011
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Yes, UPSDM has Placement Partners who assist trained candidates in finding
    jobs. The system tracks enrolled, trained, assessed, and appointed
    candidates.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    Skill Mitra Portal is available on upsdm.gov.in. Click on 'Skill Mitra
    Portal' in the navigation menu to access it.
  ────────────────────────────────────────────────────────────────────────────

  Q5. Where can I find the list of training centers in Lucknow?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          AMBIGUOUS_MATCH
  Client Latency: 42.91 ms
  Server Latency: 38.72 ms
  Source IDs:     www.upsdm.gov.in/Content/Grading_Pdf/TPGrading2025-26.pdf__chunk_010, www.upsdm.gov.in/Content/Grading_Pdf/TPGrading2024-25.pdf__chunk_016, www.upsdm.gov.in/Home/RunningSchemes__chunk_003
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    You can find training centers using the 'Search Centers' link on
    upsdm.gov.in or by visiting the Skill Development Centers page.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    I detected multiple possible topics in your question. Could you please
    rephrase or be more specific?
  ────────────────────────────────────────────────────────────────────────────

  Q6. What courses are available under UPSDM?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 36.22 ms
  Server Latency: 32.35 ms
  Source IDs:     www.upsdm.gov.in/Home/FAQ__chunk_006, www.upsdm.gov.in/Home/FAQ__chunk_000, www.upsdm.gov.in/Home/Downloads__chunk_005
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    UPSDM offers both Traditional and Futuristic job role courses across
    multiple sectors. Details are available on the Sector & Course page at
    upsdm.gov.in.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    UPSDM offers both Traditional and Futuristic job role courses across
    multiple sectors. To see the full list, visit upsdm.gov.in and click on
    'Course Details' in the navigation menu.
  ────────────────────────────────────────────────────────────────────────────

  Q7. What is Kaushal Drishti?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          FAISS_DIRECT
  Client Latency: 330.53 ms
  Server Latency: 326.88 ms
  Source IDs:     www.upsdm.gov.in/Home/Downloads__chunk_011, www.upsdm.gov.in/Home/Index__chunk_003, www.upsdm.gov.in/Home/Index__chunk_003
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Kaushal Drishti is a portal for candidate registration and skill
    development tracking under UPSDM.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    According to official UPSDM guidelines from upsdm.gov.in/Home/Downloads:
    Shiksha Samiti
    Sihora(De-empanelled)](https://www.upsdm.gov.in/Content/WebAssets/pdfFiles/BlackList_3.pdf)
    - [Care Education Trust(
    De-empanelled)](https://www.upsdm.gov.in/Content/WebAssets/pdfFiles/BlackList_3.pdf)
    - [Doctor Amritlal Ishrat Memorial Sunbeam Society(
    De-empanelled)](https://www.upsdm.gov.in/Content/WebAssets/pdfFiles/BlackList_3.pdf)
    - [Kumud Foundation( De-empanelled)](https://www.upsdm.gov.in/Content/Web
  ────────────────────────────────────────────────────────────────────────────

  Q8. What is the helpline number for UPSDM?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 39.13 ms
  Server Latency: 35.24 ms
  Source IDs:     www.upsdm.gov.in/Home/DSDP__chunk_008, www.upsdm.gov.in/Home/FAQ__chunk_000, www.upsdm.gov.in/Home/Downloads__chunk_005
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    The UPSDM Toll Free Helpline Number is 0522-4944200. Email:
    mdssdm-up[at]nic[dot]in.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    The UPSDM Toll Free Helpline Number is 0522-4944200. You can call this
    number for any help or queries related to skill development programs.
  ────────────────────────────────────────────────────────────────────────────
================================================================================
  PERSONA: TRAINING PARTNER (TP) (7 questions)
================================================================================

  Q1. How can I register my institute as a Training Partner with UPSDM?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 44.06 ms
  Server Latency: 40.42 ms
  Source IDs:     www.upsdm.gov.in/Home/FAQ__chunk_002, www.upsdm.gov.in/Home/Downloads__chunk_005, www.upsdm.gov.in/Home/BeyondVisible__chunk_004
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Training Partners can register through the Training Partners section on
    upsdm.gov.in. There are categories of TPs listed on the portal.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    To register as a Training Partner, visit upsdm.gov.in and click on
    'Training Partner' in the navigation menu. You can also apply through the
    'RFP Registration' link on the homepage.
  ────────────────────────────────────────────────────────────────────────────

  Q2. What are the infrastructure requirements for a training center?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 40.36 ms
  Server Latency: 36.40 ms
  Source IDs:     www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_008, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_005, www.upsdm.gov.in/Home/FAQ__chunk_004
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Training centers must meet NSQF-compliant infrastructure standards.
    Specific requirements depend on the sector and course being offered.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    The infrastructure requirements for setting up a training center include
    specific classroom size, lab equipment, and center space parameters.
    Please refer to the TP Empanelment Guidelines in the Downloads section on
    upsdm.gov.in.
  ────────────────────────────────────────────────────────────────────────────

  Q3. How do I claim reimbursement for candidate training?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          AMBIGUOUS_MATCH
  Client Latency: 67.60 ms
  Server Latency: 64.01 ms
  Source IDs:     www.upsdm.gov.in/Home/CourseCategory4__chunk_004, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_007, www.upsdm.gov.in/Home/Downloads__chunk_014
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Reimbursement claims are processed through the UPSDM portal. TPs need to
    submit training completion and assessment records.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    I detected multiple possible topics in your question. Could you please
    rephrase or be more specific?
  ────────────────────────────────────────────────────────────────────────────

  Q4. What is the empanelment process for new training programs?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          AMBIGUOUS_MATCH
  Client Latency: 40.49 ms
  Server Latency: 36.92 ms
  Source IDs:     www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_008, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_001, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_002
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    New training programs must be NSQF-compliant. TPs can apply through the
    RFP Registration portal on upsdm.gov.in.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    I detected multiple possible topics in your question. Could you please
    rephrase or be more specific?
  ────────────────────────────────────────────────────────────────────────────

  Q5. How to upload student attendance on the portal?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 35.47 ms
  Server Latency: 31.27 ms
  Source IDs:     www.upsdm.gov.in/Home/Downloads__chunk_013, www.upsdm.gov.in/Home/CyberSecurity__chunk_003, www.upsdm.gov.in/Home/Index__chunk_003
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Attendance is uploaded through the Skill Development Center Live Capture
    mobile app, available for download on the UPSDM portal.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    The Skill Development Center Live Capture app can be downloaded from
    upsdm.gov.in. Look for the app download link on the homepage. It is used
    for attendance tracking at training centers.
  ────────────────────────────────────────────────────────────────────────────

  Q6. What is the TP grading system?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 40.64 ms
  Server Latency: 36.79 ms
  Source IDs:     www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_007, www.upsdm.gov.in/Content/Grading_Pdf/TPGrading2025-26.pdf__chunk_009, www.upsdm.gov.in/Content/Grading_Pdf/TPGrading2025-26.pdf__chunk_006
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    UPSDM grades Training Partners annually. Grading reports for 2024-25 and
    2025-26 are available as PDF downloads on upsdm.gov.in.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    UPSDM grades Training Partners annually. Grading reports for 2024-25 and
    2025-26 are available on upsdm.gov.in. Look for the TP Grading links on
    the homepage.
  ────────────────────────────────────────────────────────────────────────────

  Q7. What happens if a TP is de-empanelled?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 32.87 ms
  Server Latency: 29.07 ms
  Source IDs:     www.upsdm.gov.in/Home/FAQ__chunk_008, www.upsdm.gov.in/Home/Downloads__chunk_011, www.upsdm.gov.in/Home/Downloads__chunk_012
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    De-empanelled TPs are listed on the De-empanelled TP List page on
    upsdm.gov.in. They lose the right to conduct training under UPSDM schemes.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    The list of de-empanelled Training Partners is available on upsdm.gov.in.
    Click on 'De-empanelled TP List' on the homepage to view it.
  ────────────────────────────────────────────────────────────────────────────
================================================================================
  PERSONA: INDUSTRIAL PARTNER (6 questions)
================================================================================

  Q1. How can our company collaborate with UPSDM for hiring skilled workforce?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          FAISS_DIRECT
  Client Latency: 231.30 ms
  Server Latency: 228.60 ms
  Source IDs:     www.upsdm.gov.in/Home/BeyondVisible__chunk_004, www.upsdm.gov.in/Home/DSDP__chunk_008, www.upsdm.gov.in/Home/Downloads__chunk_005
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Companies can collaborate as Placement Partners through the Placement
    Partner section on upsdm.gov.in.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    According to official UPSDM guidelines from
    upsdm.gov.in/Home/BeyondVisible: The registration portal of the UPSDM has
    over 49 lakh youth, who are though moderately educated in formal education
    environment but have shown an aptitude to get trained in various Skill
    development trades, which offer a huge potential of employment in the
    existing scenario and likely to boost up further in the days ahead. of
    India has standardized training norms for all the Skill development
    schemes and upscaled them a
  ────────────────────────────────────────────────────────────────────────────

  Q2. What is the Flexi MoU scheme?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 33.10 ms
  Server Latency: 29.37 ms
  Source IDs:     www.upsdm.gov.in/Home/Downloads__chunk_009, www.upsdm.gov.in/Home/Downloads__chunk_013, www.upsdm.gov.in/Home/RunningSchemes__chunk_004
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    The Flexi MoU is a scheme under UPSDM that allows flexible partnership
    agreements for skill development between industry and the mission.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    Companies can collaborate with UPSDM as Placement Partners. Visit
    upsdm.gov.in and click on 'Placement Partner' in the navigation menu for
    more details on the partnership process.
  ────────────────────────────────────────────────────────────────────────────

  Q3. Can we customize the training curriculum for our industry needs?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          AMBIGUOUS_MATCH
  Client Latency: 35.22 ms
  Server Latency: 32.21 ms
  Source IDs:     www.upsdm.gov.in/Content/WebAssets/images/resource/ProjectPraveen.pdf__chunk_001, www.upsdm.gov.in/Home/CourseCategory4__chunk_004, www.upsdm.gov.in/Home/BeyondVisible__chunk_004
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Training courses follow NSQF standards. Industry partners can work with
    Sector Skill Councils (SSC) to influence curriculum relevant to their
    sector.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    I detected multiple possible topics in your question. Could you please
    rephrase or be more specific?
  ────────────────────────────────────────────────────────────────────────────

  Q4. Are there any financial benefits or subsidies for hiring apprentices through UPSDM?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          FAISS_DIRECT
  Client Latency: 248.20 ms
  Server Latency: 244.80 ms
  Source IDs:     www.upsdm.gov.in/Home/Downloads__chunk_011, www.upsdm.gov.in/Home/BeyondVisible__chunk_004, www.upsdm.gov.in/Home/Downloads__chunk_013
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    UPSDM schemes like DDU-GKY and PMKVY provide government-funded training.
    Financial details are available in the scheme guidelines PDFs on the
    portal.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    According to official UPSDM guidelines from upsdm.gov.in/Home/Downloads:
    Shiksha Samiti
    Sihora(De-empanelled)](https://www.upsdm.gov.in/Content/WebAssets/pdfFiles/BlackList_3.pdf)
    - [Care Education Trust(
    De-empanelled)](https://www.upsdm.gov.in/Content/WebAssets/pdfFiles/BlackList_3.pdf)
    - [Doctor Amritlal Ishrat Memorial Sunbeam Society(
    De-empanelled)](https://www.upsdm.gov.in/Content/WebAssets/pdfFiles/BlackList_3.pdf)
    - [Kumud Foundation( De-empanelled)](https://www.upsdm.gov.in/Content/Web
  ────────────────────────────────────────────────────────────────────────────

  Q5. Who is the nodal officer for industry tie-ups?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          FAISS_DIRECT
  Client Latency: 228.56 ms
  Server Latency: 225.04 ms
  Source IDs:     www.upsdm.gov.in/Home/CourseCategory1__chunk_005, www.upsdm.gov.in/Home/CourseCategory4__chunk_012, www.upsdm.gov.in/Content/WebAssets/images/resource/tradition_jobrole_list.pdf__chunk_035
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Contact the SPMU (State Project Management Unit) via the Contact Us page
    on upsdm.gov.in or call 0522-4944200.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    According to official UPSDM guidelines from
    upsdm.gov.in/Home/CourseCategory1: Discharge Machine (Spark Erosion) |
    CSC/Q0121 | 4 | | 30 | Capital Goods | Service Engineer - Installation and
    Commisioning | CSC/Q0502 | 4 | | 31 | Electronics and IT Hardware | Field
    Technician Air Conditioner Level 4 | ELE/Q3102 | 4 | | 32 | Electronics
    and IT Hardware | Field Engineer –RACW | ELE/Q3105 | 5 | | 33 |
    Electronics and IT Hardware | Solar & LED Technician | ELE/Q5903 | 5 | |
    34 | Electronics and IT Har
  ────────────────────────────────────────────────────────────────────────────

  Q6. What sectors does UPSDM cover for skill training?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 37.70 ms
  Server Latency: 34.00 ms
  Source IDs:     www.upsdm.gov.in/Home/BeyondVisible__chunk_004, www.upsdm.gov.in/Home/FAQ__chunk_006, www.upsdm.gov.in/Home/Downloads__chunk_005
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    UPSDM covers multiple sectors including traditional and futuristic job
    roles. Full sector and course details are available on the Sector & Course
    page.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    UPSDM offers both Traditional and Futuristic job role courses across
    multiple sectors. To see the full list, visit upsdm.gov.in and click on
    'Course Details' in the navigation menu.
  ────────────────────────────────────────────────────────────────────────────
================================================================================
  PERSONA: GENERAL / EDGE CASES (5 questions)
================================================================================

  Q1. Hello there!
  ────────────────────────────────────────────────────────────────────────────
  Stage:          GREETING
  Client Latency: 4.98 ms
  Server Latency: 0.52 ms
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    [GREETING] Should return instant greeting template like 'Hello! I'm
    Kaushal Dost, your UPSDM assistant.'
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    Hello! I'm Kaushal Dost, your UPSDM assistant. How can I help you today? 😊
  ────────────────────────────────────────────────────────────────────────────

  Q2. Namaste!
  ────────────────────────────────────────────────────────────────────────────
  Stage:          GREETING
  Client Latency: 5.96 ms
  Server Latency: 0.77 ms
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    [GREETING] Should return a Hindi greeting template response instantly.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    नमस्ते! मैं कौशल दोस्त हूँ, आपका UPSDM सहायक। मैं आपकी कैसे मदद कर सकता
    हूँ? 😊
  ────────────────────────────────────────────────────────────────────────────

  Q3. Who is the Prime Minister of Australia?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          OUT_OF_SCOPE
  Client Latency: 37.01 ms
  Server Latency: 33.05 ms
  Source IDs:     www.upsdm.gov.in/Home/Downloads__chunk_011, www.upsdm.gov.in/Content/WebAssets/images/resource/PMKVYGuidelines(2016-2020).pdf__chunk_000, www.upsdm.gov.in/Home/PrivacyPolicy__chunk_003
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    [OUT OF SCOPE] Should trigger low-confidence fallback. Not related to
    UPSDM.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    I am the UPSDM Assistant. I can answer questions related to UPSDM schemes,
    registration, training partners, candidates, assessments and industry
    collaboration.
  ────────────────────────────────────────────────────────────────────────────

  Q4. What is the capital of France?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          OUT_OF_SCOPE
  Client Latency: 37.50 ms
  Server Latency: 33.77 ms
  Source IDs:     www.upsdm.gov.in/Home/PrivacyPolicy__chunk_004, www.upsdm.gov.in/Home/Downloads__chunk_012, www.upsdm.gov.in/Home/Downloads__chunk_011
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    [OUT OF SCOPE] Should trigger low-confidence fallback. Not related to
    UPSDM.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    I am the UPSDM Assistant. I can answer questions related to UPSDM schemes,
    registration, training partners, candidates, assessments and industry
    collaboration.
  ────────────────────────────────────────────────────────────────────────────

  Q5. Is there a helpline number for UPSDM?
  ────────────────────────────────────────────────────────────────────────────
  Stage:          STATIC_LOOKUP
  Client Latency: 40.20 ms
  Server Latency: 36.74 ms
  Source IDs:     www.upsdm.gov.in/Home/FAQ__chunk_000, www.upsdm.gov.in/Home/DSDP__chunk_008, www.upsdm.gov.in/Home/FAQ__chunk_002
  ────────────────────────────────────────────────────────────────────────────
  EXPECTED ANSWER:
    Toll Free Helpline Number 0522-4944200. Email: mdssdm-up[at]nic[dot]in.
  ────────────────────────────────────────────────────────────────────────────
  ACTUAL ANSWER:
    The UPSDM Toll Free Helpline Number is 0522-4944200. You can call this
    number for any help or queries related to skill development programs.
  ────────────────────────────────────────────────────────────────────────────


================================================================================
  SUMMARY TABLE
================================================================================
  Category                  Question                                                Stage              Latency (ms)
  ───────────────────────── ─────────────────────────────────────────────────────── ────────────────── ────────────
  Student                   What is UPSDM?                                          FAISS_DIRECT             212.61
  Student                   How can I enroll in a skill development course?         STATIC_LOOKUP             59.06
  Student                   What are the eligibility criteria for the PMKVY scheme? FAISS_DIRECT             737.76
  Student                   Do you provide placement assistance after training?     STATIC_LOOKUP             37.64
  Student                   Where can I find the list of training centers in Luc... AMBIGUOUS_MATCH           42.91
  Student                   What courses are available under UPSDM?                 STATIC_LOOKUP             36.22
  Student                   What is Kaushal Drishti?                                FAISS_DIRECT             330.53
  Student                   What is the helpline number for UPSDM?                  STATIC_LOOKUP             39.13
  Training Partner (TP)     How can I register my institute as a Training Partne... STATIC_LOOKUP             44.06
  Training Partner (TP)     What are the infrastructure requirements for a train... STATIC_LOOKUP             40.36
  Training Partner (TP)     How do I claim reimbursement for candidate training?    AMBIGUOUS_MATCH           67.60
  Training Partner (TP)     What is the empanelment process for new training pro... AMBIGUOUS_MATCH           40.49
  Training Partner (TP)     How to upload student attendance on the portal?         STATIC_LOOKUP             35.47
  Training Partner (TP)     What is the TP grading system?                          STATIC_LOOKUP             40.64
  Training Partner (TP)     What happens if a TP is de-empanelled?                  STATIC_LOOKUP             32.87
  Industrial Partner        How can our company collaborate with UPSDM for hirin... FAISS_DIRECT             231.30
  Industrial Partner        What is the Flexi MoU scheme?                           STATIC_LOOKUP             33.10
  Industrial Partner        Can we customize the training curriculum for our ind... AMBIGUOUS_MATCH           35.22
  Industrial Partner        Are there any financial benefits or subsidies for hi... FAISS_DIRECT             248.20
  Industrial Partner        Who is the nodal officer for industry tie-ups?          FAISS_DIRECT             228.56
  Industrial Partner        What sectors does UPSDM cover for skill training?       STATIC_LOOKUP             37.70
  General / Edge Cases      Hello there!                                            GREETING                   4.98
  General / Edge Cases      Namaste!                                                GREETING                   5.96
  General / Edge Cases      Who is the Prime Minister of Australia?                 OUT_OF_SCOPE              37.01
  General / Edge Cases      What is the capital of France?                          OUT_OF_SCOPE              37.50
  General / Edge Cases      Is there a helpline number for UPSDM?                   STATIC_LOOKUP             40.20
================================================================================
  Total questions tested: 26
================================================================================