"""VERIS 1.3.x A4 controlled vocabulary (canonical labels used by the gold standard).

These spellings are authoritative — do NOT alter them. The scorer treats any
predicted value not present in the relevant list as off-vocabulary (a schema
violation), and any gold/pred string match is case-sensitive against these.

CHANGELOG
  2026-06-15 (RQ2 enum-completeness audit, add-only — no values removed):
    Policy: the controlled vocabulary is the full official VERIS 1.3.x list per
    field, and MUST be a superset of every value used by gold_standard.json
    (gold is the scoring truth and is frozen). A gold-superset invariant check
    (build via check_enum_superset / Task B) found three gold values absent from
    their field's enum; each was a *real enum gap* causing a gold-correct answer
    to be scored as a schema violation. Added:
      + "Defacement"   -> action.hacking.variety
          gold GS-080 (action_category=Hacking, web-app defacement) annotates
          action_variety=["Defacement"]. In official VERIS "Defacement" is an
          attribute.integrity.variety; gold also uses it there for the same
          record. We additionally admit it as a Hacking action variety because
          gold treats web defacement as the hacking *action*, and the enum must
          cover gold. (Validation unions all action.*.variety, so membership in
          the Hacking sub-list makes it valid for action_variety.)
      + "Destroy data" -> attribute.integrity.variety
          gold GS-020 annotates attr_integrity_variety=["Destroy data", ...].
          Official VERIS lists "Destroy data" under action.malware.variety;
          gold applies it as an integrity impact (data destruction). Added so
          gold is in-vocab.
      + "Encryption"   -> attribute.availability.variety
          gold GS-026 (ransomware) annotates attr_avail_variety=["Encryption",
          "Loss"]. "Encryption" is not an official VERIS enum value, but it is a
          frozen gold label (ransomware encryption => availability loss); added
          to satisfy the superset invariant.
    NOT added: "Obscuration" to attribute.integrity.variety. The model emitted
    attr_integrity_variety=["Obscuration"] (GS-099), but in official VERIS 1.3.x
    "Obscuration" is an attribute.availability.variety (already present below),
    NOT an integrity variety, and gold never uses it. It is a genuine off-vocab
    misplacement and remains a schema violation (not remapped).
    Ref: vz-risk/veris verisc-enum.json (fetched 2026-06-15).
"""

ENUMS = {
    "actor.category": ["External", "Internal", "Partner", "Unknown"],
    "actor.external.variety": ["Activist", "Auditor", "Competitor", "Customer", "End-user", "Force majeure", "Former employee", "Nation-state", "Organized crime", "Acquaintance", "State-affiliated", "Terrorist", "Unaffiliated", "Other", "Unknown"],
    "actor.internal.variety": ["Auditor", "Call center", "Cashier", "Developer", "End-user", "Executive", "Finance", "Former employee", "Guard", "Helpdesk", "Human resources", "Maintenance", "Manager", "System admin", "Other", "Unknown"],
    "actor.partner.variety": ["Partner (third party / supply chain)"],
    "actor.motive": ["Financial", "Espionage", "Fun", "Grudge", "Ideology", "Convenience", "Fear", "Secondary", "NA", "Other", "Unknown"],
    "action.category": ["Malware", "Hacking", "Social", "Misuse", "Physical", "Error", "Environmental", "Unknown"],
    "action.malware.variety": ["Adminware", "Adware", "Backdoor", "Brute force", "Capture app data", "Capture stored data", "Click fraud / cryptomining", "Command and control (C2)", "Destroy data", "Disable controls", "DoS", "Downloader", "Exploit vuln", "Export data", "In-memory", "Packet sniffer", "Password dumper", "RAM scraper", "Ransomware", "Rootkit", "Scan network", "Spam", "Spyware/Keylogger", "SQL injection", "Trojan", "Worm", "Other", "Unknown"],
    "action.malware.vector": ["Direct install", "Download by malware", "Email attachment", "Email link", "Instant messaging", "Network propagation", "Partner", "Remote injection", "Removable media", "Software update", "Web application - drive-by", "Web application - download", "Web download", "Other", "Unknown"],
    "action.hacking.variety": ["Abuse of functionality", "Brute force / credential stuffing", "Buffer overflow", "Cache poisoning", "Cross-site request forgery (CSRF)", "Cross-site scripting (XSS)", "Cryptanalysis", "Defacement", "Denial of service (DoS)", "Footprinting / fingerprinting", "Forced browsing / predictable resource location", "Format string attack", "Fuzz testing", "HTTP request smuggling", "HTTP response splitting", "Integer overflows", "LDAP injection", "Mail command injection", "Man-in-the-middle (MitM)", "Null byte injection", "OS commanding", "Offline cracking", "Path traversal", "Remote file inclusion (RFI)", "Reverse engineering", "Routing detour", "Session fixation", "Session prediction", "Session replay", "SOAP array abuse", "Special element injection", "SQL injection (SQLi)", "SSI injection", "URL redirector abuse", "Use of backdoor or C2", "Use of stolen creds", "XML external entities (XXE)", "XML injection", "XPath injection", "Other", "Unknown"],
    "action.hacking.vector": ["3rd party desktop", "Backdoor or C2", "Command shell", "Desktop sharing software", "Hypervisor", "Inter-tenant", "LAN access", "Network propagation", "Partner", "Physical access", "VPN", "Web application", "Other", "Unknown"],
    "action.social.variety": ["Baiting", "Bribery", "Elicitation", "Extortion", "Forgery", "Influence", "Pharming", "Phishing", "Pretexting", "Propaganda", "Scam", "Spam", "Other", "Unknown"],
    "action.social.vector": ["Documents", "Email", "In-person", "Instant messaging", "Phone", "Removable media", "SMS", "Social media", "Software", "Website", "Other", "Unknown"],
    "action.misuse.variety": ["Data mishandling", "Email misuse", "Illicit content", "Knowledge abuse", "Net misuse", "Possession abuse", "Privilege abuse", "Unapproved hardware", "Unapproved software", "Unapproved workaround", "Other", "Unknown"],
    "action.misuse.vector": ["LAN access", "Non-corporate", "Physical access", "Remote access", "Other", "Unknown"],
    "action.physical.variety": ["Assault", "Connection", "Destruction", "Disabled controls", "Skimmer", "Snooping", "Surveillance", "Tampering", "Theft", "Wiretapping", "Other", "Unknown"],
    "action.physical.vector": ["Privileged access", "Visitor privileges", "Public facility", "Personal residence", "Partner facility", "Uncontrolled location", "Disabled physical", "Other", "Unknown"],
    "action.error.variety": ["Capacity shortage", "Classification error", "Data entry error", "Disposal error", "Gaffe", "Loss", "Maintenance error", "Misconfiguration", "Misdelivery", "Omission", "Physical accidents", "Programming error", "Publishing error", "Malfunction", "Other", "Unknown"],
    "action.error.vector": ["Carelessness", "Inadequate personnel", "Inadequate processes", "Inadequate technology", "Random error", "Other", "Unknown"],
    "action.environmental.variety": ["Earthquake", "EMI", "ESD", "Fire", "Flood", "Hazmat", "Humidity", "Hurricane", "Lightning", "Power failure", "Temperature", "Tornado", "Tsunami", "Vermin", "Volcanic activity", "Wind", "Other", "Unknown"],
    "asset.category": ["Server", "Network", "User Device", "Media", "Person", "Kiosk/Terminal", "Embedded", "Other", "Unknown"],
    "asset.server.variety": ["Authentication", "Backup", "Code repository", "Configuration mgmt", "Database", "DHCP", "Directory (LDAP/AD)", "Distributed control system (DCS)", "DNS", "File", "ICS", "Log", "Mail", "Mainframe", "Payment switch", "POS controller", "Print", "Proxy", "Remote access", "SCADA", "VM host", "Web application", "Other", "Unknown"],
    "asset.user_device.variety": ["ATM", "Desktop", "Gas terminal", "Kiosk", "Laptop", "Mobile phone", "Network appliance", "Payment card", "POS terminal", "Peripheral", "Tablet", "Telephone", "VoIP phone", "Other", "Unknown"],
    "asset.media.variety": ["Disk drive", "Disk media", "Documents", "Flash drive", "Payment card", "Smart card", "Tapes", "Other", "Unknown"],
    "asset.network.variety": ["Access reader", "Broadband", "Camera", "Firewall", "HSM", "IDS/IPS", "LAN", "PBX", "PLC", "Private WAN", "Public WAN", "RTU", "Router or switch", "SAN", "Telephone", "VoIP adapter", "Wireless access point (WLAN)", "Other", "Unknown"],
    "asset.person.variety": ["Auditor", "Cashier", "Customer", "Developer", "End-user", "Executive", "Finance", "Former employee", "Guard", "Helpdesk", "Human resources", "Maintenance", "Manager", "Partner", "System admin", "Other", "Unknown"],
    "asset.kiosk_terminal.variety": ["ATM", "Gas terminal", "Kiosk", "POS terminal", "Self-checkout", "Other", "Unknown"],
    "asset.embedded.variety": ["Camera", "HVAC", "ICS", "Medical device", "Peripheral", "Printer", "RFID", "Robotics", "Other", "Unknown"],
    "attribute.confidentiality.data_disclosure": ["Yes", "No", "Potentially", "Unknown"],
    "attribute.confidentiality.data.variety": ["Bank", "Classified", "Copyrighted", "Credentials", "Digital certificate", "Internal", "Medical", "Payment", "Personal", "Secrets", "Source code", "System", "Virtual currency", "Other", "Unknown"],
    "attribute.integrity.variety": ["Alter behavior", "Created account", "Defacement", "Fraudulent transaction", "Hardware tampering", "Log tampering", "Malware installation", "Misrepresentation", "Modify configuration", "Modify data", "Modify privileges", "Repurpose", "Software installation", "Destroy data", "Other", "Unknown"],
    "attribute.availability.variety": ["Acceleration", "Degradation", "Destruction", "Interruption", "Loss", "Obscuration", "Outage", "Encryption", "Other", "Unknown"],
    "yes_no": ["Yes", "No"],
    "yes_no_unknown": ["Yes", "No", "Unknown"],
    "confidence": ["High", "Medium", "Low"],
}
