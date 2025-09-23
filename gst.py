PAN_NO = {
    "AAGCT7889P",
    "AAHCT5406D",
    "AAHCD1012H",
    "AAICT6216A"
}
def gst_validations(list_of_gst):
            try:
                list_of_gst = list(set(list_of_gst))
                vendor_gst = list_of_gst[0]
                company_gst = list_of_gst[1]
                print(vendor_gst)
                for i in list_of_gst:
                    if len(i) == 15:
                        if i[2:12] in PAN_NO:
                            company_gst = i
                        else:
                            vendor_gst = i

                return {'status':True , "CompanyGstinPdf":company_gst,"VendorGstin":vendor_gst}
            except Exception as e:
                return {'status':False , "error":str(e)}
            

print(gst_validations([
    "27AAACA3640H1Z0",
    "08AAGCT7889P1Z3"
  ]))