import unittest

from pipeline import wa

PROGRAMS = [
    {"programid": "1", "programname": " Good Electric Apprenticeship ", "programstatus": "Active", "preparatoryprogram": False,
     "openshop": "Union", "programurl": "www.example.org", "approvaldate": "2020-01-02T00:00:00.000",
     "contactname": "Jane Doe", "contactemail": "jane@example.org", "contactphone": "(555) 555-0100", "physicaladdress": "1 Main St"},
    {"programid": "2", "programname": "Old Program", "programstatus": "Cancelled", "preparatoryprogram": False},
    {"programid": "3", "programname": "Prep Program", "programstatus": "Active", "preparatoryprogram": True},
]
OCCS = [
    {"programid": "1", "programoccupationid": "10", "occupationname": "Electrician", "occupationstatus": "Active",
     "soccode": "47-2111.00", "socdescription": "Electricians", "termhours": "8000", "rsihours": "576", "step1wage": "20.5", "journeywage": "41"},
    {"programid": "1", "programoccupationid": "11", "occupationname": "Helper", "occupationstatus": "InActive", "step1wage": "18"},
    {"programid": "1", "programoccupationid": "12", "occupationname": "No Wage", "occupationstatus": "Active", "step1wage": None},
    {"programid": "1", "programoccupationid": "13", "occupationname": "Odd", "occupationstatus": "Active", "step1wage": "30", "journeywage": "12"},
    {"programid": "2", "programoccupationid": "20", "occupationname": "Cancelled", "occupationstatus": "Active", "step1wage": "25"},
    {"programid": "3", "programoccupationid": "30", "occupationname": "Prep", "occupationstatus": "Active", "step1wage": "17"},
]
COUNTIES = [{"programid": "1", "statecode": "WA", "countyname": "KING"}, {"programid": "1", "statecode": "ID", "countyname": "LATAH"}]


class ListingTests(unittest.TestCase):
    def setUp(self):
        self.listings = wa.build_listings(PROGRAMS, OCCS, COUNTIES)

    def test_only_active_paid_registered_occupations(self):
        self.assertEqual(sorted(x["id"] for x in self.listings), ["10", "13"])

    def test_no_personal_data(self):
        text = repr(self.listings)
        for gone in ("Jane", "jane@", "555", "Main St"):
            self.assertNotIn(gone, text)

    def test_fields(self):
        x = next(x for x in self.listings if x["id"] == "10")
        self.assertEqual((x["program"], x["start_wage"], x["journey_wage"], x["term_hours"], x["counties"]),
                         ("Good Electric Apprenticeship", 20.5, 41.0, 8000, ["King"]))
        self.assertEqual(x["program_url"], "https://www.example.org")
        self.assertTrue(x["source"].startswith("https://data.wa.gov/resource/") and x["source"].endswith("=10"))
        odd = next(x for x in self.listings if x["id"] == "13")
        self.assertIsNone(odd["journey_wage"])   # a journey wage below the starting wage is not shown

    def test_helpers(self):
        self.assertEqual(wa.clean_url("example.com/x"), "https://example.com/x")
        self.assertEqual(wa.clean_url("not a url"), "")
        self.assertEqual(wa.clean_url("someone@example.com"), "")
        self.assertIsNone(wa.money("abc"))
        self.assertIsNone(wa.money("0"))


if __name__ == "__main__":
    unittest.main()
