from fpdf import FPDF
import csv
import json
import os

def update_to_json_file(update, filename: str):
    update_dict = update.to_dict()
    json_update = json.dumps(update_dict, indent=4)
    
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(json_update)


def cleanup(file_paths):
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File {file_path} has been removed.")
        else:
            print(f"File {file_path} does not exist.")


# pdf with answer
def gen_pdf(quizname: str, isanswer: bool=False):
    
    filename = quizname
    parts = filename.split("-")
    module = parts[0].split("/")[-1]
    subject = parts[1]
    topic = parts[2].split(".")[0]
    ans_indentation = 7
    ans_height = 7
    outputname = filename.split("/")[-1].split(".")[0]

    class PDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                # Setting font
                self.set_font("helvetica", "I", 16)
                # draw the module
                self.cell(0, 10, module, align="L")
                # draw the subject
                self.cell(0, 10, subject, align="R")
                self.ln(7)
                self.set_font("helvetica", "B", 20)
                # Printing title:
                # Calculate the width of the centered text
                text_width = self.get_string_width(topic)
                # Calculate the x-coordinate to center the text
                x = (self.w - text_width) / 2
                self.set_x(x)
                # Center-aligned text
                self.cell(w=text_width + 7, h=10, text=topic, border=0, align="C")
                self.ln()
            else:
                self.ln()


        def footer(self):
            # Position cursor
            self.set_y(-7)
            self.set_x(-1)
            # Setting font: helvetica italic 8
            self.set_font("helvetica", "I", 8)
            # Printing page number:
            self.cell(4, 10, text=f"Page {self.page_no()}/{{nb}}", align="R")


    pdf = PDF("P", "mm", "A4")
    pdf.set_margins(left=5, top=0, right=5)
    pdf.set_auto_page_break(auto=True, margin=15)
    ans_indentation = pdf.l_margin + ans_indentation

    pdf.add_page()

    # Open the CSV file and read it as a DictReader
    with open(filename,'r') as file:
        csv_reader = csv.DictReader(file)
        # print questions and options
        for row in csv_reader:
            pdf.set_font("helvetica", 'B', size=18)
            pdf.cell(0, 10, f"{row['sn']}. {row['question']} ({row['source']})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", size=16)
            # Conditionally add options
            for option in ['a', 'b', 'c', 'd', 'e', 'f', 'g']:
                # reset the color
                pdf.set_fill_color(255, 255, 255)
                option_text = row.get(option)  # Use .get() to handle None values
                if option_text is not None and option_text.strip():  # Check if the option is not None and not an empty string
                    pdf.set_x(ans_indentation)
                    # higlight the correct answer
                    if isanswer:
                        if option == row["answer"].strip():
                            pdf.set_fill_color(255, 255, 0)
                    # pdf.cell(0, ans_height, f"{option}) {option_text}", new_x="LMARGIN", new_y="NEXT", fill=True)
                    # Calculate the dimensions of the rectangle based on the text size
                    text_width = pdf.get_string_width(f"{option}) {option_text}")
                    text_height = pdf.font_size
                    pdf.rect(pdf.get_x(), pdf.get_y(), text_width + 2, text_height + 1, round_corners=True, style='F')  # 'F' fills the rectangle
                    pdf.cell(0, ans_height, f"{option}) {option_text}", new_x="LMARGIN", new_y="NEXT")

            pdf.ln(2)
        
        # print answer in table
        file.seek(0)
        csv_reader = csv.DictReader(file)
        pdf.ln(10)
        pdf.set_font("helvetica", "B", 20)
        pdf.set_fill_color(255, 255, 0)
        pdf.cell(0, 15, f"The Answers", align="C" ,new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Times", "IB", 20)
        counter = 0
        for row in csv_reader:
            pdf.cell(45, 15, f"{row['sn']} - {row['answer']}")
            # Increment the counter
            counter += 1
            # Check if the counter reaches 5
            if counter == 5:
                pdf.ln()
                counter = 0


    pdf.ln()
    if isanswer:
        path = f"./temp/{outputname}_Answered.pdf"
    else:
        path = f"./temp/{outputname}.pdf"
    pdf.output(path)
    return path 