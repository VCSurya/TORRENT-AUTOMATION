
from itertools import combinations
from difflib import SequenceMatcher , get_close_matches
import json
import re

JSON = {'status': True, 'data': {'Gst': ['27AAJCG7930M1Z1', '08AAHCD1012H1Z4'], 'InvoiceNo': '', 'InvoiceDate': '2025-9-2', 'InvoiceAmount': '254880', 'IrnNo': 'b2547493c01d23694118ff858500b9c6efe1f540e48a4ff7b7d50f08dd68647', 'PoNo': 'RJDP/P02/1101635/34000773', 'PAN Numbers': ['AAJCG7930M'], 'Email Id': 'sales@greenglobe.world', 'SesGrn': ['5-180487', '5000180487']}, 'text': 'TAX INVOICE\nGREENGLOBE FUEL SOLUTIONS PVT. LTD.\nUNIT NO. 1-5, BUILDING NO. 05, RADHE KRISHNA INDUSTRIAL PARK\nSURVEY NO. 65, MUMBAI-NASHIK ROAD, VILLAGE- PIMPLAS, TAL-\nBHIWANDI THANE-421302, MAHARASHTRA, INDIA\nMobile No. - Dispatch : 7718801145\nBilling & Documents : 7718801149 / 50\nEMAIL: sales@greenglobe.world, ggaccounts@greenglobe.world;\nCIN-U23200MH2022PTC383112\nIRN No. :-\nbb2547493c01d23694118ff858500b9c6efe1f540e48a4ff7b7d5\n0f08dd68647\nE-way Billl No. :\n282030608715\nGSTIN No\n27AAJCG7930M1Z1\nSTATE CODE\n27\nInvoice No\nPAN No\nAAJCG7930M\nInvoice Date\nPO No.\nRJDP/P02/1101635/34000773 DATED 03.07.2025\nPAYMENT TERMS\n45 Days\nDELIVERY TERMS\nLR No\nNA\nLR DATE\n30/08/2025\nNO OF PACKAGES\n5\nGROSS WEIGHT\nINSURANCE\nTata AIG\nGeneral\nCO NAME\n384\nTRANSPORTER\nARC TRANSPORT\nPOLICY NO\nC003500058\nDETAILS OF PURCHASER(BILLED TO)\nOriginal for Recipient\nGGPL2526/242\n30/08/2025\nDOOR DELIVERY\nTIME OF PREPARATION\n16.00\n16.18\nTIME OF REMOVAL\nPLACE OF REMOVAL\nFactory Gate\nDETAILS OF CONSIGNEE\nDHOLPUR CGD PVT LTD\n2nd Floor, Gopal Complex, Nursing Road, Top Tiraha,\nDholpur-328001\nRAJASTHAN\nINDIA\nDHOLPUR CGD PVT LTD\nNEAR LIC OFFICE, DHOLPUR E-118,RIICO INDUSTRIAL AREA,\nONDELA ROAD,\nDHOLPUR-328001\nRAJASTHAN\n50000180033\nGSTIN NO\n08AAHCD1012H1Z4\nGSTIN No\n:\n08AAHCD1012H1Z4\nSr\nNo\nLiem Code\nDescription Of Goods / Service\nTax\nRate\n18.00 %\nQuantity\nUOM\n1\nFGSMO0308;\nService Regulator Module 100 SCMH\nHSN /SAC\nCode\n84811000\n2\nFGSM003118\nService Regulator Module 200 SCMH\n84811000\n18.00 %\n4\nNOS\n46500.00\nReceived Date :\n15/9/25\nPO No.\nGRN /SE No.\n5-180487\nIV Posting No.\nDCC Control No .:\n91416\n5000180487\nTerms And Conditions\n1. All Disputes Are Subject To Mumbai Jurisdiction.\n2. Goods Once Sold Will Not Be Taken Back.\n3. Our Risk And Responsibility Ceases On Delivery Of Goods .\n4. Interest @ 18% Will Be Charged On All Over Due Invoices. E & O.E.\nTotal GST Amount : INR Thirty-Eight Thousand Eight Hundred Eighty Only\nInvoice Value :INR Two Lakhs Fifty-Four Thousand Eight Hundred Eighty Only\nBANK DETAILS\n:\nAXIS BANK LTD. BRANCH : MULUND WEST\nBE FUEL SOLU\nTIONS PV\nACCOUNT NO\n922030041665561\nIFSC NO\nUTIBC000108\nADDRESS\nMULUND WEST, MUMBAI [MH], MUMBAI 400080\n1302+\nRate\nINR\nAmount\nINR\n30,000.00\n1\nNOS\n30000.00\n186,000.00\nTotal Amount Before Tax\n216000.00\nDiscount\n0.00\nIGST@18\n38880.00\nTotal GST :\nGrand Total (INR) :\n38880.00\n254,880.00\nFor GREENGLOBE FUEL SOLUTIONS PVT. LTD.\nSlaque\nAuthorised Signatory\nRegistered Office . GREENGLOBE FUFI SOLUTIONS PVT LTD, UNIT NO. 1.5 BUILDING NO.05 , RADHE KRISHNA INDUSTRIAL PARK, SURVEY NO.65/4 , MUMBAI NACHIK\nROAD. VILLAGE-PIMPLAS .TAL BHIWANDI , THANE - 421302 . MAHARASTRA INDIA\nSAP\nPrint Time : 15:22:33\nPrinled by SAP Business One\nPage 1 of 1', 'cordinates': {'TAX': [1, 3.99, 0.9, 0.12, 0.63], 'INVOICE': [1, 4.25, 0.9, 0.13, 0.93], 'GREENGLOBE': [1, 1.15, 10.51, 0.11, 0.86], 'FUEL': [1, 6.23, 9.7, 0.11, 0.62], 'SOLUTIONS': [1, 1.82, 10.52, 0.1, 0.8], 'PVT.': [1, 6.99, 9.69, 0.12, 0.6], 'LTD.': [1, 7.2, 9.69, 0.12, 0.59], 'UNIT': [1, 2.53, 10.53, 0.1, 0.57], 'NO.': [1, 2.72, 10.53, 0.1, 0.52], '1-5,': [1, 2.11, 1.46, 0.11, 0.56], 'BUILDING': [1, 2.99, 10.53, 0.1, 0.73], '05,': [1, 2.93, 1.46, 0.11, 0.55], 'RADHE': [1, 3.59, 10.54, 0.1, 0.64], 'KRISHNA': [1, 3.86, 10.54, 0.1, 0.68], 'INDUSTRIAL': [1, 4.16, 10.54, 0.1, 0.83], 'PARK': [1, 4.38, 1.47, 0.1, 0.62], 'SURVEY': [1, 4.82, 10.56, 0.09, 0.67], '65,': [1, 2.22, 1.6, 0.11, 0.53], 'MUMBAI-NASHIK': [1, 2.37, 1.6, 0.12, 1.15], 'ROAD,': [1, 4.62, 5.05, 0.1, 0.67], 'VILLAGE-': [1, 3.46, 1.6, 0.11, 0.78], 'PIMPLAS,': [1, 3.86, 1.6, 0.11, 0.82], 'TAL-': [1, 4.3, 1.61, 0.11, 0.58], 'BHIWANDI': [1, 1.51, 10.64, 0.1, 0.76], 'THANE-421302,': [1, 2.16, 1.74, 0.12, 1.06], 'MAHARASHTRA,': [1, 2.84, 1.74, 0.11, 1.12], 'INDIA': [1, 3.05, 10.66, 0.09, 0.61], 'Mobile': [1, 1.67, 1.88, 0.11, 0.7], 'No.': [1, 2.51, 7.46, 0.17, 0.65], '-': [1, 2.19, 10.65, 0.09, 0.44], 'Dispatch': [1, 2.22, 1.89, 0.11, 0.76], ':': [1, 1.85, 10.8, 0.11, 0.46], '7718801145': [1, 2.68, 1.89, 0.11, 0.92], 'Billing': [1, 1.67, 2.02, 0.11, 0.66], '&': [1, 2.95, 9.05, 0.11, 0.46], 'Documents': [1, 2.05, 2.03, 0.11, 0.89], '7718801149': [1, 2.64, 2.03, 0.11, 0.92], '/': [1, 3.19, 5.92, 0.1, 0.45], '50': [1, 3.25, 2.03, 0.12, 0.51], 'EMAIL:': [1, 1.67, 2.17, 0.11, 0.7], 'sales@greenglobe.world,': [1, 1.99, 2.17, 0.12, 1.51], 'ggaccounts@greenglobe.world;': [1, 3.12, 2.17, 0.12, 1.77], 'CIN-U23200MH2022PTC383112': [1, 1.67, 2.31, 0.11, 1.62], 'IRN': [1, 0.71, 2.54, 0.1, 0.54], ':-': [1, 1.06, 2.55, 0.09, 0.48], 'bb2547493c01d23694118ff858500b9c6efe1f540e48a4ff7b7d5': [1, 1.66, 2.53, 0.11, 3.06], '0f08dd68647': [1, 1.66, 2.68, 0.1, 0.95], 'E-way': [1, 0.71, 2.85, 0.11, 0.66], 'Billl': [1, 0.99, 2.85, 0.11, 0.56], '282030608715': [1, 1.67, 2.86, 0.1, 1.02], 'GSTIN': [1, 4.23, 5.64, 0.1, 0.63], 'No': [1, 2.7, 7.65, 0.17, 0.56], '27AAJCG7930M1Z1': [1, 1.56, 3.03, 0.11, 1.14], 'STATE': [1, 2.78, 3.05, 0.09, 0.62], 'CODE': [1, 3.02, 3.05, 0.09, 0.62], '27': [1, 3.74, 3.05, 0.1, 0.49], 'Invoice': [1, 0.57, 9.4, 0.12, 0.72], 'PAN': [1, 0.71, 3.24, 0.09, 0.54], 'AAJCG7930M': [1, 1.54, 3.24, 0.1, 0.88], 'Date': [1, 2.56, 6.88, 0.15, 0.72], 'PO': [1, 1.85, 7.09, 0.14, 0.55], 'RJDP/P02/1101635/34000773': [1, 1.54, 3.45, 0.12, 1.67], 'DATED': [1, 2.82, 3.46, 0.12, 0.68], '03.07.2025': [1, 3.12, 3.46, 0.11, 0.88], 'PAYMENT': [1, 0.65, 3.64, 0.1, 0.77], 'TERMS': [1, 4.62, 3.65, 0.1, 0.66], '45': [1, 1.54, 3.65, 0.1, 0.49], 'Days': [1, 1.65, 3.66, 0.1, 0.58], 'DELIVERY': [1, 6.02, 3.66, 0.09, 0.77], 'LR': [1, 0.7, 4.05, 0.1, 0.5], 'NA': [1, 1.53, 3.89, 0.09, 0.52], 'DATE': [1, 0.83, 4.05, 0.1, 0.62], '30/08/2025': [1, 5.77, 3.25, 0.11, 0.91], 'NO': [1, 0.78, 10.05, 0.1, 0.53], 'OF': [1, 5.77, 4.49, 0.1, 0.52], 'PACKAGES': [1, 2.87, 3.88, 0.1, 0.81], '5': [1, 3.5, 3.9, 0.09, 0.45], 'GROSS': [1, 2.63, 4.05, 0.1, 0.66], 'WEIGHT': [1, 2.9, 4.05, 0.1, 0.72], 'INSURANCE': [1, 4.18, 3.9, 0.09, 0.87], 'Tata': [1, 4.79, 3.94, 0.1, 0.57], 'AIG': [1, 4.99, 3.94, 0.1, 0.53], 'General': [1, 4.79, 4.09, 0.1, 0.72], 'CO': [1, 4.19, 4.04, 0.09, 0.5], 'NAME': [1, 4.32, 4.04, 0.09, 0.65], '384': [1, 3.49, 4.09, 0.1, 0.56], 'TRANSPORTER': [1, 0.7, 4.26, 0.1, 1.02], 'ARC': [1, 1.53, 4.27, 0.1, 0.57], 'TRANSPORT': [1, 1.72, 4.27, 0.11, 0.91], 'POLICY': [1, 4.18, 4.27, 0.1, 0.68], 'C003500058': [1, 4.81, 4.29, 0.1, 0.94], 'DETAILS': [1, 0.85, 9.64, 0.1, 0.75], 'PURCHASER(BILLED': [1, 2.13, 4.47, 0.13, 1.24], 'TO)': [1, 3.01, 4.47, 0.12, 0.56], 'Original': [1, 6.89, 0.93, 0.11, 0.73], 'for': [1, 7.24, 0.94, 0.11, 0.52], 'Recipient': [1, 7.38, 0.95, 0.12, 0.79], 'GGPL2526/242': [1, 5.78, 3.05, 0.1, 1.05], 'DOOR': [1, 5.77, 3.66, 0.09, 0.63], 'TIME': [1, 5.77, 4.09, 0.1, 0.6], 'PREPARATION': [1, 6.11, 3.86, 0.09, 0.93], '16.00': [1, 6.98, 3.87, 0.1, 0.64], '16.18': [1, 6.97, 4.11, 0.1, 0.65], 'REMOVAL': [1, 6.15, 4.27, 0.1, 0.8], 'PLACE': [1, 5.76, 4.27, 0.1, 0.65], 'Factory': [1, 7.0, 4.29, 0.11, 0.74], 'Gate': [1, 7.36, 4.29, 0.1, 0.6], 'CONSIGNEE': [1, 5.91, 4.48, 0.11, 0.92], 'DHOLPUR': [1, 4.99, 4.91, 0.11, 0.82], 'CGD': [1, 4.69, 4.7, 0.11, 0.57], 'PVT': [1, 2.24, 10.53, 0.1, 0.52], 'LTD': [1, 5.1, 4.7, 0.11, 0.55], '2nd': [1, 0.7, 4.87, 0.11, 0.55], 'Floor,': [1, 0.87, 4.87, 0.11, 0.65], 'Gopal': [1, 1.14, 4.87, 0.11, 0.65], 'Complex,': [1, 1.41, 4.87, 0.12, 0.81], 'Nursing': [1, 1.84, 4.87, 0.12, 0.73], 'Road,': [1, 2.19, 4.87, 0.12, 0.64], 'Top': [1, 2.46, 4.87, 0.12, 0.55], 'Tiraha,': [1, 2.64, 4.88, 0.12, 0.68], 'Dholpur-328001': [1, 0.69, 5.01, 0.11, 1.09], 'RAJASTHAN': [1, 4.23, 5.34, 0.09, 0.89], 'NEAR': [1, 4.23, 4.91, 0.1, 0.64], 'LIC': [1, 4.49, 4.91, 0.1, 0.53], 'OFFICE,': [1, 4.64, 4.91, 0.11, 0.72], 'E-118,RIICO': [1, 5.46, 4.91, 0.12, 0.89], 'AREA,': [1, 6.51, 4.91, 0.12, 0.65], 'ONDELA': [1, 4.24, 5.05, 0.1, 0.74], 'DHOLPUR-328001': [1, 4.24, 5.2, 0.1, 1.17], '50000180033': [1, 5.38, 5.36, 0.22, 2.01], '08AAHCD1012H1Z4': [1, 4.91, 5.65, 0.1, 1.25], 'Sr': [1, 0.66, 5.82, 0.08, 0.48], 'Liem': [1, 1.02, 5.89, 0.09, 0.57], 'Code': [1, 4.23, 6.01, 0.1, 0.62], 'Description': [1, 2.25, 5.92, 0.11, 0.89], 'Of': [1, 2.46, 8.92, 0.11, 0.49], 'Goods': [1, 2.58, 8.92, 0.11, 0.62], 'Service': [1, 1.7, 6.49, 0.1, 0.66], 'Tax': [1, 6.36, 8.22, 0.1, 0.54], 'Rate': [1, 6.3, 5.84, 0.09, 0.6], '18.00': [1, 4.87, 6.51, 0.09, 0.61], '%': [1, 5.13, 6.51, 0.09, 0.46], 'Quantity': [1, 5.32, 5.92, 0.1, 0.79], 'UOM': [1, 5.82, 5.91, 0.09, 0.59], '1': [1, 7.55, 10.8, 0.1, 0.46], 'FGSMO0308;': [1, 0.98, 6.15, 0.09, 0.91], 'Regulator': [1, 1.98, 6.49, 0.1, 0.77], 'Module': [1, 2.37, 6.5, 0.1, 0.7], '100': [1, 2.7, 6.17, 0.09, 0.54], 'SCMH': [1, 2.85, 6.5, 0.1, 0.62], 'HSN': [1, 4.22, 5.87, 0.11, 0.57], '/SAC': [1, 4.43, 5.87, 0.11, 0.62], '84811000': [1, 4.26, 6.51, 0.09, 0.78], '2': [1, 0.68, 6.5, 0.08, 0.44], 'FGSM003118': [1, 0.97, 6.49, 0.09, 0.91], '200': [1, 2.7, 6.5, 0.1, 0.54], '4': [1, 5.49, 6.52, 0.07, 0.44], 'NOS': [1, 5.84, 6.18, 0.09, 0.59], '46500.00': [1, 6.26, 6.53, 0.1, 0.8], 'Received': [1, 1.85, 6.88, 0.15, 1.05], '15/9/25': [1, 3.06, 6.75, 0.26, 1.49], 'GRN': [1, 1.85, 7.26, 0.17, 0.67], '/SE': [1, 2.18, 7.26, 0.17, 0.6], '5-180487': [1, 3.01, 7.17, 0.24, 1.71], 'IV': [1, 1.85, 7.46, 0.17, 0.53], 'Posting': [1, 2.02, 7.46, 0.17, 0.86], 'DCC': [1, 1.85, 7.65, 0.17, 0.7], 'Control': [1, 2.2, 7.65, 0.17, 0.87], '.:': [1, 2.88, 7.65, 0.17, 0.52], '91416': [1, 3.16, 7.58, 0.22, 1.16], '5000180487': [1, 1.96, 7.93, 0.23, 2.15], 'Terms': [1, 0.59, 8.51, 0.1, 0.64], 'And': [1, 1.0, 8.91, 0.11, 0.55], 'Conditions': [1, 1.01, 8.51, 0.1, 0.81], '1.': [1, 0.59, 8.64, 0.1, 0.47], 'All': [1, 2.01, 9.04, 0.11, 0.5], 'Disputes': [1, 0.79, 8.64, 0.1, 0.72], 'Are': [1, 1.14, 8.65, 0.1, 0.53], 'Subject': [1, 1.29, 8.65, 0.1, 0.69], 'To': [1, 1.59, 8.65, 0.1, 0.49], 'Mumbai': [1, 1.7, 8.65, 0.1, 0.72], 'Jurisdiction.': [1, 2.04, 8.65, 0.11, 0.87], '2.': [1, 0.59, 8.77, 0.11, 0.47], 'Once': [1, 0.94, 8.77, 0.11, 0.59], 'Sold': [1, 1.15, 8.77, 0.11, 0.56], 'Will': [1, 1.26, 9.04, 0.11, 0.54], 'Not': [1, 1.49, 8.78, 0.1, 0.55], 'Be': [1, 1.42, 9.04, 0.11, 0.5], 'Taken': [1, 1.78, 8.78, 0.1, 0.61], 'Back.': [1, 2.02, 8.78, 0.1, 0.6], '3.': [1, 0.58, 8.91, 0.11, 0.47], 'Our': [1, 0.67, 8.91, 0.11, 0.54], 'Risk': [1, 0.83, 8.91, 0.11, 0.56], 'Responsibility': [1, 1.17, 8.91, 0.11, 0.93], 'Ceases': [1, 1.71, 8.91, 0.12, 0.66], 'On': [1, 1.88, 9.04, 0.11, 0.51], 'Delivery': [1, 2.12, 8.91, 0.11, 0.71], '.': [1, 2.5, 10.65, 0.1, 0.43], '4.': [1, 0.57, 9.03, 0.11, 0.47], 'Interest': [1, 0.66, 9.04, 0.11, 0.7], '@': [1, 0.98, 9.04, 0.11, 0.47], '18%': [1, 1.08, 9.04, 0.11, 0.56], 'Charged': [1, 1.54, 9.04, 0.11, 0.72], 'Over': [1, 2.13, 9.05, 0.11, 0.59], 'Due': [1, 2.33, 9.05, 0.11, 0.55], 'Invoices.': [1, 2.5, 9.05, 0.11, 0.75], 'E': [1, 2.87, 9.05, 0.11, 0.45], 'O.E.': [1, 3.03, 9.05, 0.11, 0.56], 'Total': [1, 6.08, 9.46, 0.11, 0.6], 'GST': [1, 6.06, 9.26, 0.11, 0.56], 'Amount': [1, 5.67, 8.22, 0.09, 0.75], 'INR': [1, 7.12, 5.98, 0.09, 0.56], 'Thirty-Eight': [1, 1.61, 9.22, 0.12, 0.91], 'Thousand': [1, 2.32, 9.41, 0.13, 0.82], 'Eight': [1, 2.76, 9.42, 0.12, 0.61], 'Hundred': [1, 3.0, 9.42, 0.13, 0.79], 'Eighty': [1, 3.41, 9.42, 0.13, 0.67], 'Only': [1, 3.71, 9.43, 0.13, 0.61], 'Value': [1, 0.91, 9.4, 0.12, 0.62], ':INR': [1, 1.16, 9.4, 0.12, 0.6], 'Two': [1, 1.4, 9.4, 0.12, 0.57], 'Lakhs': [1, 1.6, 9.41, 0.12, 0.65], 'Fifty-Four': [1, 1.88, 9.41, 0.13, 0.83], 'BANK': [1, 1.65, 9.63, 0.1, 0.59], 'AXIS': [1, 1.49, 9.63, 0.1, 0.55], 'BRANCH': [1, 2.03, 9.64, 0.1, 0.68], 'MULUND': [1, 1.48, 10.27, 0.09, 0.69], 'WEST': [1, 2.72, 9.64, 0.1, 0.6], 'BE': [1, 4.41, 9.69, 0.14, 0.53], 'SOLU': [1, 4.76, 9.65, 0.16, 0.61], 'TIONS': [1, 4.94, 9.76, 0.23, 0.56], 'PV': [1, 5.03, 10.02, 0.1, 0.48], 'ACCOUNT': [1, 0.58, 9.85, 0.1, 0.83], '922030041665561': [1, 1.49, 9.85, 0.09, 0.99], 'IFSC': [1, 0.57, 10.05, 0.11, 0.59], 'UTIBC000108': [1, 1.49, 10.05, 0.09, 0.87], 'ADDRESS': [1, 0.58, 10.27, 0.1, 0.8], 'WEST,': [1, 1.79, 10.27, 0.09, 0.6], 'MUMBAI': [1, 5.46, 10.56, 0.09, 0.72], '[MH],': [1, 2.32, 10.27, 0.1, 0.58], '400080': [1, 2.83, 10.28, 0.09, 0.64], '1302+': [1, 4.7, 10.3, 0.16, 0.65], '30,000.00': [1, 7.23, 6.2, 0.1, 0.82], '30000.00': [1, 6.27, 6.2, 0.11, 0.8], '186,000.00': [1, 7.17, 6.53, 0.1, 0.88], 'Before': [1, 6.04, 8.22, 0.1, 0.69], '216000.00': [1, 7.19, 8.22, 0.11, 0.85], 'Discount': [1, 6.12, 8.39, 0.1, 0.78], '0.00': [1, 7.45, 8.41, 0.1, 0.59], 'IGST@18': [1, 6.12, 8.58, 0.11, 0.8], '38880.00': [1, 7.19, 9.27, 0.1, 0.8], 'Grand': [1, 5.79, 9.46, 0.11, 0.67], '(INR)': [1, 6.3, 9.46, 0.12, 0.65], '254,880.00': [1, 7.14, 9.46, 0.11, 0.87], 'For': [1, 5.46, 9.7, 0.1, 0.55], 'Slaque': [1, 6.04, 9.81, 0.43, 1.03], 'Authorised': [1, 5.98, 10.35, 0.1, 0.87], 'Signatory': [1, 6.47, 10.35, 0.11, 0.81], 'Registered': [1, 0.53, 10.51, 0.11, 0.75], 'Office': [1, 0.9, 10.51, 0.11, 0.6], 'FUFI': [1, 1.63, 10.52, 0.11, 0.57], 'LTD,': [1, 2.37, 10.53, 0.1, 0.55], '1.5': [1, 2.86, 10.53, 0.1, 0.51], 'NO.05': [1, 3.34, 10.54, 0.1, 0.6], ',': [1, 1.89, 10.65, 0.1, 0.43], 'PARK,': [1, 4.6, 10.55, 0.09, 0.6], 'NO.65/4': [1, 5.11, 10.56, 0.09, 0.68], 'NACHIK': [1, 5.79, 10.56, 0.09, 0.66], 'ROAD.': [1, 0.53, 10.63, 0.11, 0.6], 'VILLAGE-PIMPLAS': [1, 0.75, 10.64, 0.11, 0.98], '.TAL': [1, 1.35, 10.64, 0.1, 0.55], 'THANE': [1, 1.94, 10.65, 0.1, 0.63], '421302': [1, 2.25, 10.65, 0.1, 0.64], 'MAHARASTRA': [1, 2.56, 10.65, 0.1, 0.88], 'SAP': [1, 6.17, 10.85, 0.08, 0.55], 'Print': [1, 1.38, 10.79, 0.11, 0.61], 'Time': [1, 1.62, 10.8, 0.11, 0.6], '15:22:33': [1, 1.94, 10.8, 0.11, 0.77], 'Prinled': [1, 5.79, 10.84, 0.09, 0.64], 'by': [1, 6.06, 10.84, 0.09, 0.49], 'Business': [1, 6.34, 10.84, 0.09, 0.72], 'One': [1, 6.67, 10.84, 0.1, 0.55], 'Page': [1, 7.07, 10.8, 0.11, 0.63], 'of': [1, 7.42, 10.8, 0.1, 0.51]}}

SAP_API = {
    "InwardRefNo" : "",
    "SourceOfDoc" : "",
    "DocMailPerson" : "",
    "InwardDate" : "",
    "PoLpo" : "",
    "GaName" : "",
    "CompanyGstinPdf" : "", 
    "CCompanyGstinPdf" : "",
    "CompanyGstinSap" : "",
    "VendorName" : "",
    "VendorGstin" : "",
    "CVendorGstin" : "",
    "InvoiceNo" : "",
    "CInvoiceNo" : "",
    "InvoiceDate" : "",
    "CInvoiceDate" : "",
    "InvoiceAmount" : "",
    "CInvoiceAmount" : "",
    "PoLpoIoNoPdf" : "",
    "CPoLpoIoNo" : "",
    "IrnNo" : "",
    "CIrnNo" : "",
    "MsmeNo" : "",
    "Status" : "Draft",
    "ModeOfEntry" : "Manual",
    "CreatedOn" : "",
    "CreatedBy" : "",
    "ChangedOn" : "",
    "ChangedBy" : "",
    "FileName" : "",
    "ErrorNo" : "",
    "ErrorMsg" : "",
    "ErrorType" : "",
    "Flag" : "A",
    "DCCHEADERTODCCSES" : []
}

gst_no = {
    "24AAGCT7889P1Z9",
    "24AAGCT7889P2Z8",
    "27AAGCT7889P1Z3",
    "27AAGCT7889P1Z3",
    "03AAGCT7889P1ZD",
    "34AAGCT7889P1Z8",
    "08AAGCT7889P1Z3",
    "08AAGCT7889P1Z3",
    "33AAGCT7889P1ZA",
    "36AAGCT7889P1Z4",
    "09AAGCT7889P1Z1",
    "24AAHCT5406D1ZO",
    "33AAHCT5406D1ZP",
    "24AAHCD1012H1ZA",
    "08AAHCD1012H1Z4",
    "24AAICT6216A1ZR",
    "08AAICT6216A1ZL"
}

def convert_normalized_to_absolute(cordinates):
        x0 = cordinates[1] * 72
        y0 = cordinates[2] * 72
        x1 = x0 + cordinates[3] * 72
        y1 = y0 + cordinates[4] * 72
        return f"{x0},{y0},{x1},{y1}"


def gst_validations(list_of_gst):
    try:
        list_of_gst = list(set(list_of_gst))
        company_gst = list_of_gst[0]
        vendor_gst = list_of_gst[1]

        for i in list_of_gst:
            if len(i) == 15:
                if i in gst_no:
                    company_gst = i
                else:
                    vendor_gst = i

        return {'status':True , "CompanyGstinPdf":company_gst,"VendorGstin":vendor_gst}
    except Exception as e:
        return {'status':False , "error":str(e)}

def get_irn_number(lst):
    """
    Takes a list of strings and returns the first string of exactly 64 characters.
    - If any item itself is 64 chars → return it directly.
    - Otherwise, try all possible combinations of items in sequence order.
    - If no such string exists → return empty string.
    """
    # 1️⃣ Direct check: any single item of length 64
    for item in lst:
        if len(item) == 64:
            return item

    n = len(lst)
    # 2️⃣ Try all possible combinations
    for r in range(2, n+1):  # size of combination
        for indices in combinations(range(n), r):
            merged = "".join(lst[i] for i in indices)
            if len(merged) == 64:
                return merged

    # 3️⃣ No solution
    return ""

def get_closest_10_digit_string(text, input_string):
    # Extract all 10-digit substrings using regular expressions
    potential_matches = re.findall(r'\d{10}', text)

    if not potential_matches:
        return None, 0  # If no 10-digit numbers are found
    
    # Initialize variables to store the best match and its similarity
    best_match = None
    highest_similarity = 0

    # Function to calculate similarity using SequenceMatcher
    def calculate_similarity(str1, str2):
        return SequenceMatcher(None, str1, str2).ratio()

    # Compare each 10-digit substring with the input string
    for match in potential_matches:
        similarity = calculate_similarity(input_string, match)
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = match

    return best_match, highest_similarity

gst_result = gst_validations(JSON['data']['Gst'])

if gst_result['status']:
    SAP_API['CompanyGstinPdf'] = gst_result['CompanyGstinPdf']
    SAP_API['VendorGstin'] = gst_result['VendorGstin']

SAP_API['IrnNo'] = JSON['data']['IrnNo'] 
if len(JSON['data']['IrnNo']) != 64:
    pattern = r'\b(?=[0-9a-fA-F]*[a-fA-F])(?=[0-9a-fA-F]*[0-9])[0-9a-fA-F]{10,64}\b'
    matches = re.findall(pattern, JSON['text']) # Find all matches
    res = get_irn_number(matches)
    SAP_API['IrnNo'] = res


total_scs_no = []

for index, data in enumerate(set(JSON['data']['SesGrn'])):
    
    ses_no = data

    # Check if data is not exactly 10-digit numeric
    if not (len(data) == 10 and data.isdigit()):
        closest_string, similarity = get_closest_10_digit_string(JSON['text'], data)
        if closest_string:
            ses_no = closest_string  # replace with closest match
    
    if ses_no not in total_scs_no:
        
        SAP_API['DCCHEADERTODCCSES'].append(
            {
                "InwardRefNo": "",
                "PoNo": "",
                "SesGrnScrollNoPdf": ses_no,
                "ItemNo": f"{index+1}",
                "SesGrnScrollNoSap": "",
                "ParkDocNo": "",
                "Amount": JSON['data']['InvoiceAmount'],
                "CreatedOn": "",
                "Zindicator": "",
                "CreatedBy": "",
                "CSesGrnScrollNoPdf": "",
                "ChangedOn": "",
                "ChangedBy": ""
            }
        )

        total_scs_no.append(ses_no)


SAP_API['InvoiceNo'] = JSON['data']['InvoiceNo']
SAP_API['InvoiceDate'] = JSON['data']['InvoiceDate'].replace("-","")
SAP_API['InvoiceAmount'] = JSON['data']['InvoiceAmount']
SAP_API['PoLpoIoNoPdf'] = JSON['data']['PoNo'].split('/')[-1]


def find_closest(data: dict, target: str) -> str:

    keys = list(data.keys())
    
    # Try to get best match with cutoff
    matches = get_close_matches(target, keys, n=1, cutoff=0.6)
    
    if matches:
        return matches[0]
    
    # If nothing above cutoff, fallback to absolute closest
    best_match = max(keys, key=lambda k: SequenceMatcher(None, target, k).ratio())
    return best_match


all_keys = [i for i in JSON['cordinates']]
# print(SAP_API)
word_to_find = "FGSMO0308"
closest_key = find_closest(JSON['cordinates'], word_to_find)
result = convert_normalized_to_absolute(JSON['cordinates'][closest_key])
print(result)
print(type(result))

# for i ,v in enumerate(JSON['cordinates']):
#     if len(v) > 2:
#         print(i)
#         print(v)