"""Templates for Ontario solicitors (Land Titles, Teraview, charges, PPSA).

⚠️ Ontario uses solicitors, NOT notaries. No notarial acts. Charges are registered
on Teraview (Land Titles) or under the PPSA for personal property.
"""

TEMPLATES_SOLICITOR_ON = {
    # 1. Transmission of file package
    "solicitor_on_file_package": """Dear Counsel,

Please find below the complete file package for the following matter:

▸ File         : Borrower [NAME] — [Construction / Acquisition / Refinance]
▸ Property     : [ADDRESS], [CITY], ON [POSTAL]
▸ PIN          : [PIN — 9 digits]
▸ Closing date : [DD MONTH YYYY]

Documents transmitted:
1. Loan agreement signed by the borrower
2. Engagement letter countersigned
3. Schedule B (if applicable)
4. Personal property security agreement (PPSA — for assignment/discharge)
5. Borrower ID

We would be grateful to receive:
- The draft Charge / Standard Charge Terms at least 72 hours prior to closing
- A pre-closing parcel register and writ search
- Confirmation of registration on Teraview within 24 hours of closing

Please do not hesitate to contact us for any coordination matter.""",

    # 2. Pre-closing diligence
    "solicitor_on_pre_closing": """Dear Counsel,

In connection with file [BORROWER NAME — TYPE], could you kindly forward:

1. The current parcel register and writ search for PIN [PIN]
2. Confirmation of available charge priority
3. Title insurance policy reference (if applicable)
4. The draft Charge for our review (at least 72 hours before closing on
   [DD MONTH YYYY])

We rely on this information to coordinate the funding instructions in a
timely manner.""",

    # 3. Post-closing follow-up
    "solicitor_on_post_closing": """Dear Counsel,

Further to the closing of [BORROWER NAME — TYPE] on [DD MONTH YYYY], please
confirm:

1. That the Charge has been registered on Teraview
2. The instrument number and registration date
3. The final parcel register reflecting our charge in the agreed priority
4. Any post-closing undertakings outstanding on your file

If anything was deferred or remains pending, please advise so we can update
our internal trackers accordingly.""",

    # 4. Discharge of charge
    "solicitor_on_discharge_charge": """Dear Counsel,

Following full repayment by [BORROWER NAME] in file [FILE REF], we hereby
authorize the discharge of the Charge registered as instrument
[INSTRUMENT NUMBER] on PIN [PIN].

Please proceed with the registration of a Discharge of Charge on Teraview
in due course and provide us with:
1. A copy of the executed Discharge
2. The new instrument number once registered
3. An updated parcel register confirming the discharge""",

    # 5. Redirection — wrong jurisdiction (a notary in QC tries to act for ON)
    "solicitor_on_jurisdiction_redirect": """Dear [Notary / Counsel],

Thank you for your message. Please note that the property at issue
([ADDRESS, CITY, ON]) is located in Ontario and falls under the
Land Titles Act / Registry Act jurisdiction. Closings on Ontario
properties must be conducted by an Ontario solicitor (no notarial act
applies in this province).

If you wish, we can introduce you to one of our Ontario coordinating
solicitors to ensure the file proceeds without delay.

Kindly let us know how you wish to proceed.""",
}
