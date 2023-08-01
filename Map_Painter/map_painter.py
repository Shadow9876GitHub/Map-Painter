import numpy as np
import cv2
import tkinter 
from tkinter import colorchooser
from tkinter import filedialog
from tkinter.ttk import *
import time
from PIL import Image, ImageTk
import os
from pathlib import Path
import sys

def showImage(img) -> None:
    cv2.imshow("Image",img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def hex_to_bgr(hexa: str) -> (int, int, int):
    return tuple(int(hexa[i:i+2], 16)  for i in (5, 3, 1))

def valid_hex(hex: str) -> bool:
    if len(hex)!=7 or hex==line_colour_hex: return False
    for i in hex[1:]:
        if i not in "0123456789ABCDEF":
            return False
    return True

#General map information
ROOT="maps/"
base=[None, None, None, None, None, None, None]
BW=0
NORM=1 if os.path.exists(f'{ROOT}map.png') else -10000
if NORM<0: ROOT='/'.join(filedialog.askopenfilename().replace("\\","/").split("/")[:-1])+"/"
NORM=1 if os.path.exists(f'{ROOT}map.png') else -10000
if NORM<0: raise Exception(f'{ROOT}map.png was not found! Perhaps the specified file is in another directory...')
if not os.path.exists(f'app_data.data'):
    with open(f"app_data.data","w") as file:
        file.write("")
SUB=2 if os.path.exists(f'{ROOT}subregions.png') else -10000
REG=3 if os.path.exists(f'{ROOT}regions.png') else -10000
COU=4 if os.path.exists(f'{ROOT}countries.png') else -10000
EMP=5 if os.path.exists(f'{ROOT}empires.png') else -10000
CONT=6 if os.path.exists(f'{ROOT}continents.png') else -10000
attributes=["","colour","subregion","region","country","empire","continent"]
if SUB<=-1:
    REG-=1; COU-=1; EMP-=1; CONT-=1
    attributes.remove("subregion")
if REG<=-1:
    COU-=1; EMP-=1; CONT-=1
    attributes.remove("region")
if COU<=-1:
    EMP-=1; CONT-=1
    attributes.remove("country")
if EMP<=-1:
    CONT-=1
    attributes.remove("empire")
if CONT<=-1:
    attributes.remove("continent")

def read_file(path):
    im_path = Path(path)
    curr_dir = os.getcwd()
    os.chdir(im_path.parent)
    bgrImage=cv2.imread(im_path.name)
    os.chdir(curr_dir)
    return bgrImage

base[NORM]=read_file(f'{ROOT}map.png')
_,base[BW]=cv2.threshold(cv2.cvtColor(base[NORM], cv2.COLOR_BGR2GRAY),0,255,0) #Make thresholded image (black and white)
if SUB>=0: base[SUB]=read_file(f'{ROOT}subregions.png')
if REG>=0: base[REG]=read_file(f'{ROOT}regions.png')
if COU>=0: base[COU]=read_file(f'{ROOT}countries.png')
if EMP>=0: base[EMP]=read_file(f'{ROOT}empires.png')
if CONT>=0: base[CONT]=read_file(f'{ROOT}continents.png')
line_colour_hex="#000000"
line_colour=hex_to_bgr(line_colour_hex)
base=[i for i in base if type(i)!=None]

headers=[]

def add_to_history(elem: str) -> None:
    if not update_history: return
    parts=elem.replace("change","").replace(" from "," to ").split(" to ")
    if parts[1]==parts[2]: return
    history.append(elem)
    undo_history.clear()

def undo(event) -> None:
    global selected, update_history, is_country
    if len(history)==0: return
    update_history=False
    message=history.pop(-1)
    undo_history.append(message)
    message=[i.strip() for i in message.replace("change","").replace(" from "," to ").split(" to ")]
    if message[0]=="selected" and str(selected)==message[2].replace("*",""):
        is_country="*" in message[1]
        old_provinces=message[1].replace("[","").replace("]","").replace("*","").split(",")
        selected=[] if old_provinces[0]=="" else list(map(int,old_provinces))
        update_provinces_map()
        display_map(BW if selected!=[] else displayed_map)
        if selected!=[]:
            show_information(selected[-1],is_country)
    else:
        if is_country:
            change_country_attr(provinces[selected[0]].colour,message[0],message[1])
        else:
            old_vals=message[1].replace("[","").replace("]","").replace("*","").replace('\'',"").replace("\"","").split(",")
            old_vals=[i.strip() for i in old_vals]
            for i,elem in enumerate(selected):
                change_province(elem,message[0],old_vals[i])
    update_history=True

def redo(event) -> None:
    global selected, update_history, is_country
    if len(undo_history)==0: return
    update_history=False
    message=undo_history.pop(-1)
    history.append(message)
    message=[i.strip() for i in message.replace("change","").replace(" from "," to ").split(" to ")]
    if message[0]=="selected" and str(selected)==message[1].replace("*",""):
        is_country="*" in message[2]
        new_provinces=message[2].replace("[","").replace("]","").replace("*","").split(",")
        selected=[] if new_provinces[0]=="" else list(map(int,new_provinces))
        update_provinces_map()
        display_map(BW if selected!=[] else displayed_map)
        if selected!=[]:
            show_information(selected[-1],is_country)
    else:
        if is_country:
            change_country_attr(provinces[selected[0]].colour,message[0],message[2])
        else:
            change_provinces(selected,message[0],message[2])
    update_history=True

history=[]
undo_history=[]
update_history=True

#Starting widget
root=tkinter.Tk()

root.title("MapPainter.exe")
root.config(cursor="circle")

platform="linux"

#Zoomed state (Maximising window size)
try:
    #Linux
    root.attributes('-zoomed', True)
except:
    #Windows
    platform="windows"
    root.state('zoomed')

#General widget state information
selected=[]
is_country=False
last_selected=-1
displayed_map=1
current_map=1
cursor_position=1000

move_center=None
scale=1
latest_scale=scale
map_position=(0,0)
image_size=base[0].shape
display_size=base[0].shape if base[0].shape[0]<root.winfo_screenheight()-400 else (root.winfo_screenheight()-400,root.winfo_screenwidth())

def change_focus(event) -> None:
    event.widget.focus_set()

def set_cursor_position(widget) -> None:
    def set_c_position(widget) -> None:
        global cursor_position
        val=widget.index(tkinter.INSERT) if widget.index(tkinter.INSERT)!=len(widget.get()) else 10000
        cursor_position=val
    root.after(1,lambda widget=widget: set_c_position(widget))

def focus_to_map(event) -> None:
    map_label.focus_set()

def create_image(img) -> ImageTk.PhotoImage:
    image=cv2.resize(img,(int(img.shape[1]*scale),int(img.shape[0]*scale)),interpolation=cv2.INTER_NEAREST)
    image=image[max(map_position[0],0):max(map_position[0]+display_size[0],0),max(map_position[1],0):max(map_position[1]+display_size[1],0)]
    sign0=np.sign(map_position[0])
    if sign0==0: sign0=1
    sign1=np.sign(map_position[1])
    if sign1==0: sign1=1
    return ImageTk.PhotoImage(image=Image.fromarray(cv2.merge(current:=cv2.split(cv2.copyMakeBorder(image, max(-sign0*(display_size[0]-image.shape[0]),0), max(sign0*(display_size[0]-image.shape[0]),0), max(-sign1*(display_size[1]-image.shape[1]),0), max(sign1*(display_size[1]-image.shape[1]),0), cv2.BORDER_CONSTANT, None, value = 0))[::-1])))

#Images
images=[create_image(im) for im in base if im is not None]
map_label=tkinter.Label(root, image=images[NORM])
map_label.pack()
map_label.focus_set()
#Information

information=[tkinter.Frame(root),[],[],[]]
c_information_len=0
for _ in range(3+len(attributes)):
    information[1].append(tkinter.Label(information[0],text=""))
    information[2].append(tkinter.Entry(information[0]))
    information[3].append(tkinter.Button(information[0],text="🎨"))
    i=len(information[1])-1
    information[2][-1].bind("<Up>",lambda e,i=i: [information[2][(i-1) if (i-1)>=0 else c_information_len-1].focus_set(),information[2][(i-1) if (i-1)>=0 else c_information_len-1].icursor(cursor_position)])
    information[2][-1].bind("<Down>",lambda e,i=i: [information[2][(i+1) if (i+1)<c_information_len else 0].focus_set(),information[2][(i+1) if (i+1)<c_information_len else 0].icursor(cursor_position)])
    information[2][-1].bind("<Left>", lambda e,i=i: set_cursor_position(information[2][i]))
    information[2][-1].bind("<Right>", lambda e,i=i: set_cursor_position(information[2][i]))
    information[2][-1].bind("<Button-1>", lambda e,i=i: set_cursor_position(information[2][i]))
information[0].pack()
information[2][0].bind("<Return>",lambda e: [select_provinces(e.widget.get()),focus_to_map(e)])

def display_map(index: int, from_zoom=False) -> None:
    global selected,last_selected,displayed_map,current_map,latest_scale,BW_new,images
    if not from_zoom and latest_scale!=scale:
        images=[create_image(im) for im in base if im is not None]
        latest_scale=scale
        BW_new=True
    map_label["image"]=images[index]
    current_map=index
    if index!=BW:
        if not BW_new:
            images[BW]=create_image(base[BW])
            BW_new=True
        #History
        old_selected=f"{selected}{'*' if is_country else ''}"
        selected=[]
        if old_selected!="[]":
            add_to_history(f"change selected from {old_selected} to {selected}") #Updating history
        displayed_map=index
        last_selected=-1
        for i in information[1:]:
            for j in i:
                j.grid_forget()

#Modes: 0-normal, 1-no_multiple_select, 2-control, 3-shift
def select_province(event, input_mode=0) -> None:
    global selected,last_selected,is_country
    try:
        temp=base[NORM][int((map_position[0]+event.y)/scale),int((map_position[1]+event.x)/scale)]
    except:
        return
    is_line=True
    for i in range(3):
        is_line=is_line and temp[i]==line_colour[i]
    if not is_line:
        old_selected=f"{selected}{'*' if is_country else ''}"
        is_country=False
        reset_last_selected=False
        if input_mode==0 and len(selected)>=2:
            selected=[]
        ind=get_prov_index(int((map_position[1]+event.x)/scale), int((map_position[0]+event.y)/scale))
        if input_mode==1 or (input_mode!=3 and len(selected)==0):
            selected=[ind]
        elif input_mode!=3 and last_selected!=ind:
            selected.append(ind)
        elif last_selected==ind:
            attr=attributes[displayed_map]
            select=[i for i,e in enumerate(provinces) if getattr(e,attr)==getattr(provinces[ind],attr)]
            if input_mode==0: selected=select
            elif input_mode==2: selected+=select
            else: selected=[i for i in selected if i not in select]
            if displayed_map==NORM and input_mode==0:
                is_country=countries.get(provinces[ind].colour)!=None
            reset_last_selected=True
        else:
            if ind in selected:
                selected.remove(ind)
        selected=sorted(list(set(selected)))
        add_to_history(f"change selected from {old_selected} to {selected}{'*' if is_country else ''}") #Updating history
        last_selected=ind if not reset_last_selected else -1
        update_provinces_map()
        if len(selected)==1 and input_mode==3: ind=selected[0]
        show_information(ind,is_country)
        display_map(BW if len(selected)!=0 else displayed_map)
    elif input_mode not in (2,3):
        display_map(displayed_map)

def select_neighbours(event) -> None:
    global selected
    if len(selected)==0: return
    selected=list(set(selected).union(*[provinces[i].neighbours for i in selected]))
    update_provinces_map()
    display_map(BW)
    show_information(selected[-1],False)

def show_information(ind: int, is_country: bool) -> None:
    global c_information_len
    if len(selected)==0:
        for i in range(1,len(information)):
            for j in range(len(information[i])):
                information[i][j].grid_forget()
        c_information_len=0
    elif not is_country and len(selected)==1:
        for i in range(len(attributes)+1):
            for column in range(1,len(information)):
                information[column][i].grid(row=i,column=column-1)
            if i!=0:
                attr=(["neighbours"]+attributes[1:])[i-1]
                information[2][i].unbind("<Return>")
                information[2][i].bind("<Return>",lambda e, ind=ind, attr=attr: [change_province(ind, attr, e.widget.get()),focus_to_map(e)])
                information[3][i]["command"]=""
                information[3][i].unbind("<Return>")
                if attr in attributes[1:]:
                    information[3][i]["command"]=(lambda e=information[2][i], attr=attr: colour_chooser(e,attr))
                    information[3][i].bind("<Return>",lambda event,e=information[2][i], attr=attr: colour_chooser(e,attr))
            if information[3][i]["command"]=="":
                information[3][i].grid_forget()
            information[1][i]["text"]=(["Selected province:","Neighbours:","Owner:"]+[i.capitalize()+":" for i in attributes[2:]])[i]
            information[2][i].delete(0,10000)
            msg=ind if i==0 else getattr(provinces[ind],attr)
            if type(msg)==set and len(msg)==0:
                msg="{}"
            information[2][i].insert(0,msg)
        for i in range(len(attributes)+1,len(attributes)+3):
            for j in range(1,len(information)):
                information[j][i].grid_forget()
        c_information_len=1+len(attributes)
    elif not is_country:
        li=selected[0] in provinces[selected[1]].neighbours
        arr1=["Selected provinces:","Connection:","Owner:"]+[i.capitalize()+":" for i in attributes[2:]]
        arr2=[selected,li]+[getattr(provinces[ind],i) for i in attributes[1:]]
        if len(selected)!=2:
            arr1.remove("Connection:")
            arr2.remove(li)
        for i in range(len(arr1)):
            for column in range(1,len(information)):
                information[column][i].grid(row=i,column=column-1)
            information[1][i]["text"]=arr1[i]
            information[2][i].delete(0,10000)
            information[2][i].insert(0,str(arr2[i]))
            information[3][i]["command"]=""
            information[3][i].unbind("<Return>")
            if i>=len(arr1)-len(attributes[1:]):
                attr=attributes[1:][i-(1 if len(arr1)!=len(attributes)+1 else 2)]
                information[2][i].unbind("<Return>")
                information[2][i].bind("<Return>",lambda e, inds=selected, attr=attr: [change_provinces(inds, attr, e.widget.get()),focus_to_map(e)])
                information[3][i]["command"]=(lambda e=information[2][i], attr=attr: colour_chooser(e,attr))
                information[3][i].bind("<Return>",lambda event,e=information[2][i], attr=attr: colour_chooser(e,attr))
            elif i==1:
                information[2][i].unbind("<Return>")
                information[2][i].bind("<Return>",lambda e, selected=selected: [change_connection(*selected, e.widget.get()),focus_to_map(e)])
            if information[3][i]["command"]=="":
                information[3][i].grid_forget()
        for i in range(len(arr1),len(attributes)+3):
            for j in range(1,len(information)):
                information[j][i].grid_forget()
        c_information_len=len(arr1)
    else:
        country=countries[provinces[ind].colour]
        ls=[f"{selected}*",f"{country.name.replace('_',' ')} ({country.tag})"]+[getattr(provinces[ind],i) for i in attributes[1:]]+[country.overlord,None if country.civil_war==None else country.civil_war.replace('_',' ')]
        for i in range(len(attributes)+3):
            for column in range(1,len(information)):
                information[column][i].grid(row=i,column=column-1)
            information[1][i]["text"]=(["Selected provinces:","Country:"]+[i.capitalize()+":" for i in attributes[1:]]+["Overlord:","Civil war:"])[i]
            information[2][i].delete(0,10000)
            information[2][i].insert(0,str(ls[i]))
            information[3][i]["command"]=""
            information[3][i].unbind("<Return>")
            if i!=0:
                colour=provinces[selected[0]].colour
                attr=(["tag_name"]+attributes[1:]+["overlord","civil_war"])[i-1]
                information[2][i].unbind("<Return>")
                information[2][i].bind("<Return>",lambda e, colour=colour, attr=attr: [change_country_attr(colour, attr, e.widget.get()),focus_to_map(e)])
                if attr in attributes[1:]:
                    information[3][i]["command"]=(lambda e=information[2][i], attr=attr: colour_chooser(e,attr,True))
                    information[3][i].bind("<Return>",lambda event,e=information[2][i], attr=attr: colour_chooser(e,attr,True))
            if information[3][i]["command"]=="":
                information[3][i].grid_forget()
        c_information_len=len(attributes)+3

def colour_chooser(widget, attr: str, is_country=False) -> None:
    colour=colorchooser.askcolor(title ="Colour Chooser")[1]
    if colour!=None and len(colour)==7:
        colour=colour.upper()
        widget.delete(0,10000)
        widget.insert(0,colour)
        if not is_country:
            change_provinces(selected,attr,colour)
        else:
            change_country_attr(provinces[selected[0]].colour,attr,colour)
        focus_to_map(None)

def select_provinces(vals: str) -> None:
    try:
        global selected, is_country
        if ".." in vals:
            nums=[list(map(int,i.split(","))) for i in vals.replace("[","").replace("]","").replace("*","").split("..")]
            provs=[]
            for i in range(len(nums)-1):
                if len(nums[i])>=2:
                    provs+=nums[i][:-2]
                    provs+=list(range(nums[i][-2],nums[i+1][0]+1,nums[i][-1]-nums[i][-2]))
                else:
                    provs+=list(range(nums[i][-1],nums[i+1][0]+1))
            provs+=nums[-1][1:]
            provs=sorted(list(set(provs)))
        elif "#" in vals:
            attr=attributes[displayed_map]
            provs=sorted([i for i,p in enumerate(provinces) if getattr(p,attr)==vals])
            if len(provs)!=0 and attr=="colour": vals+="*"
        else:
            provs=sorted(list(set(map(int,vals.replace("[","").replace("]","").replace("*","").split(",")))))
        old_selected=f"{selected}{'*' if is_country else ''}"
        is_country = "*" in vals and sorted([i for i,prov in enumerate(provinces) if prov.colour==provinces[provs[0]].colour])==provs
        selected=provs
        add_to_history(f"change selected from {old_selected} to {selected}{'*' if is_country else ''}") #Updating history
        update_provinces_map()
        show_information(0 if len(selected)==0 else selected[0], is_country)
        display_map(BW)
    except:
        On_Screen_Warning("Syntax error occured during trying to change selection! Selection must be a sequence of numbers separated by a comma (eg.: [1, 2, 3])!")

#Map changes
def change_country_attr(colour: str, attr: str, val: str) -> None:
    if colour in countries:
        if attr!="tag_name":
            val=val.replace(" ","_")
            if attr=="overlord" and (len(val)!=3 or val not in [countries[i].tag for i in countries]):
                On_Screen_Warning(f"Syntax error occured during changing a country's ({countries[colour].tag}) overlord! Either value ({val}) is not appropriate or wasn't found amongst the countries' tags!")
                return
            if attr in attributes[1:] and not valid_hex(val):
                On_Screen_Warning(f"Syntax error occured during changing a country's ({countries[colour].tag}) {attr}! The value of {val} is either not a valid hexadecimal colour or disallowed!")
                return
            if attr not in attributes[1:]:
                old_val=str(getattr(countries[colour], attr))
            else:
                old_val=str(getattr(provinces[selected[0]],attr))
            setattr(countries[colour], attr, val)
            if attr in attributes[1:]:
                [(setattr(provinces[j],attr,val),update_maps(attr, j)) for j,elem in enumerate(provinces) if elem.colour==colour]
            if attr=="colour" and val!=colour:
                countries[val]=countries[colour]
                del(countries[colour])
            add_to_history(f"change {attr} from {old_val} to {val}") #Updating history
        else:
            #Changing country name and tag
            try:
                name=val.split("(")[0].strip().replace(" ","_")
                tag=val.split("(")[1].replace(")","").replace(" ","")
                if len(tag)!=3 or tag.upper()!=tag:
                    On_Screen_Warning(f"Syntax error occured while changing a country's ({countries[colour].name}) tag! \"{tag}\" is not an appropriate value for a tag, because a tag needs to be upper case and 3 letters long!")
                    return
                elif tag in [i for i in unique_tags if countries[colour].tag!=i]:
                    On_Screen_Warning(f"This tag ({tag}) already exists (and is the tag of {[countries[i].name for i in countries if countries[i].tag==tag][0]})!")
                    return
                unique_tags.remove(countries[colour].tag)
                unique_tags.append(tag)
                old_tag=getattr(countries[colour], "tag")
                old_name=getattr(countries[colour], "name")
                setattr(countries[colour], "tag", tag)
                setattr(countries[colour], "name", name)
                add_to_history(f"change tag_name from {old_name}({old_tag}) to {name}({tag})") #Updating history
            except:
                On_Screen_Warning(f"Syntax error occured while changing a country's ({countries[colour].name}) name and tag! \"{val}\" is not an appropriate value as a name and tag is required in this field with the following syntax: \"name (tag)\"")

def change_provinces(inds: [int], attr: str, val: str) -> None:
    global update_history
    update_history=False #Lock history in place
    if valid_hex(val): old_val=str([getattr(provinces[i],attr) for i in inds])
    for ind in inds:
        change_province(ind, attr, val)
    update_history=True #Allow history to be updated
    if valid_hex(val): add_to_history(f"change {attr} from {old_val} to {val}") #Updating history

def change_province(ind: int, attr: str, val: str) -> None:
    if attr!="neighbours":
        if not valid_hex(val):
            On_Screen_Warning(f"This colour ({val}) is either not valid or unusable! Please try another one!")
            return
        if attr=="colour" and val not in countries:
            countries[val]=generate_country(val)
        old_val=str(getattr(provinces[ind], attr))
        setattr(provinces[ind], attr, val)
        update_maps(attr, ind)
        add_to_history(f"change {attr} from {old_val} to {val}") #Updating history
    else:
        try:
            neighbours=set(map(int,val.replace("}","").replace("{","").split(",")))
            diff_a = neighbours - provinces[ind].neighbours
            diff_b = provinces[ind].neighbours - neighbours
            for i in diff_a:
                provinces[i].neighbours.add(ind)
            for i in diff_b:
                provinces[i].neighbours.discard(ind)
            old_neighbours=str(provinces[ind].neighbours)
            provinces[ind].neighbours=neighbours
            add_to_history(f"change neighbours from {old_neighbours} to {neighbours}") #Updating history
            update_provinces_map()
            display_map(BW)
        except:
            On_Screen_Warning(f"Syntax error occured during changing neighbours of a province ({ind})! Perhaps something was mistyped...")

def change_connection(ind1: int, ind2: int, val: str) -> None:
    try:
        old_val=ind2 in provinces[ind1].neighbours
        val={"true":True,"false":False}[val.lower()]
        if val:
            provinces[ind1].neighbours.add(ind2)
            provinces[ind2].neighbours.add(ind1)
        else:
            provinces[ind1].neighbours.discard(ind2)
            provinces[ind2].neighbours.discard(ind1)
        add_to_history(f"change connection from {old_val} to {val}") #Updating history
    except:
        On_Screen_Warning(f"An error occured while trying to change the connection between two provinces ({ind1} and {ind2}): The connection value must be a boolean (True or False) and not \"{val}\"!")

BW_new=True

#Map updates
#Updating black and white map
def update_provinces_map() -> None:
    global BW_new
    img=np.copy(base[BW])
    fill=set().union(*[provinces[i].neighbours for i in selected]).difference(set(selected))
    for i in fill:
        cv2.floodFill(img,None,provinces[i].pos,(0,0,0),flags=8|(255<<8))
    images[BW]=create_image(img)
    BW_new=False
    del(img)

def update_maps(which: str, prov_ind: int) -> None:
    ind=attributes.index(which)
    cv2.floodFill(base[ind],None,provinces[prov_ind].pos,hex_to_bgr(getattr(provinces[prov_ind],which)),flags=8|(255<<8))
    images[ind]=create_image(base[ind])

#Provinces
class Province:
    def __init__(self, colour: str, pos: (int, int)):
        self.colour=colour
        self.pos=pos
        self.neighbours={}
        self.subregion=line_colour_hex
        self.region=line_colour_hex
        self.country=line_colour_hex
        self.empire=line_colour_hex
        self.continent=line_colour_hex
        self.box=None

#Get map data related to Provinces
def get_provinces(path: str) -> [Province]:
    global headers
    ROOT='/'.join(path.replace("\\","/").split("/")[:-1])
    if not os.path.exists(f"{ROOT}/map_data.txt"): return []
    with open(f"{ROOT}/map_data.txt","r") as file:
        data=file.read().splitlines()
    #If there is some data
    if len(data)!=0:
        headers=data[0].split()
        provinces=[None]*(len(data)-1)
        #Reading results from file line by line
        for i,elem in enumerate(data[1:]):
            elem=elem.split()
            #Getting index of current province in data
            ind=i if "index" not in headers else int(elem[headers.index("index")])
            col=elem[headers.index("colour")]
            #Getting position based on headers
            pos=tuple(map(int,elem[headers.index("position"):headers.index("position")+2]))
            #Getting neighbours based on headers
            neighbours=set(map(int,elem[headers.index("neighbours")+4:]))
            #Creating a new province
            provinces[ind]=Province(col,pos)
            #Assigning attributes and values to current province
            for j in attributes[2:]:
                if j in headers:
                    setattr(provinces[ind],j,elem[headers.index(j)+4])
            #Getting province shape (boundingRect)
            provinces[ind].box=tuple(map(int,elem[headers.index("box")+1:headers.index("box")+5]))
            #Assigning neighbours
            provinces[ind].neighbours=neighbours
        return provinces
    else:
        raise Exception(f"The file \"{ROOT}/map_data.txt\" is empty! Perhaps a wrong path was given...")

def get_prov_index(x: int, y: int) -> int:
    try:
        is_line=True
        for i in range(3):
            is_line=is_line and base[NORM][y,x][i]==line_colour[i]
        if is_line: return -1
        cv2.floodFill(base[BW],None,(x,y),1,flags=8|(255<<8)) #Floodfill the thresholded image with white
        temp=cv2.inRange(base[BW],1,1)
        box=cv2.boundingRect(temp) #Getting shape of selected province
        ind=[i for i,elem in enumerate(provinces) if elem.box==box][0]
        cv2.floodFill(base[BW],None,(x,y),255,flags=8|(255<<8)) #Flooding it with white (to reset it)
        return ind
    except:
        return -1

#Countries
class Country:
    def __init__(self, tag: str, name: str, colour: str, civil_war = None):
        self.tag=tag
        self.name=name.split("-of-")[0]
        self.colour=colour
        self.civil_war=civil_war
        self.overlord=None if len(name.split("-of-"))==1 else name.split("-of-")[1]

def generate_countries() -> None:
    for i in provinces:
        colour=i.colour
        if colour not in countries:
            countries[colour]=generate_country(colour)

def generate_country(colour: str) -> Country:
    for i in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for j in range(100):
            tag=f"{i}{j:02}"
            if tag not in unique_tags:
                unique_tags.append(tag)
                return Country(tag,tag,colour)

def get_countries(path: str) -> {str: Country}:
    if not os.path.exists(path): return dict()
    with open(path,"r") as file:
        data=[i.split() for i in file.read().splitlines()]
    c=dict()
    for i in data:
        c[i[2]]=Country(*i)
    return c

#Warnings and errors
def On_Screen_Warning(message: str) -> None:
    formatted_message=""
    length=0
    for i in message.split():
        length+=len(i)
        if length>35:
            formatted_message+="\n"
            length=len(i)
        else:
            formatted_message+=" "
        formatted_message+=i
    error_message["text"]=formatted_message
    error_message.place(relx=0.5,rely=0.1,anchor=tkinter.CENTER)
    root.after(5000,error_message.place_forget)
    print(message)

#Scripting
def scripting_line(current: str) -> None:
    global output_destination

    def get_attribute(abbr: str) -> str:
        attr={"c":"colour","s":"subregion","r":"region","n":"neighbours","o":"overlord","t":"tag_name","e":"empire","k":"continent"}[abbr[0]]
        if abbr[:2]=="ci": attr="civil_war"
        if abbr[:3]=="cou": attr="country"
        if abbr[:3]=="con": attr="connection"
        if abbr[:4]=="cont": attr="continent"
        return attr

    if current.lower()[0]=="z" or current.lower()=="undo":
        undo(None)
    elif current.lower()[0]=="y" or current.lower()=="redo":
        redo(None)
    elif current.lower()[0]=="c":
        #Syntax: (c col #FFFFFF) or (change colour #FFFFFF); c - colour, s - subregion, r - region, n - neighbours, o - overlord, ci - civil_war, t - tag_name
        attr=get_attribute(current.lower().split(" ")[1])
        if attr=="connection":
            change_connection(*selected, current.split()[2].lower())
            return
        val="".join(current.split(" ")[2:])
        if is_country:
            change_country_attr(provinces[selected[0]].colour, attr, val)
        else:
            change_provinces(selected, attr, val)
    elif current.lower()[0]=="g":
        attr=get_attribute(current.lower().split(" ")[1])
        if attr=="connection":
            standard_output(selected[0] in provinces[selected[1]].neighbours)
            return
        if is_country:
            if attr in attributes[1:]:
                standard_output(getattr(provinces[selected[0]], attr))
            elif attr=="tag_name":
                standard_output(f"{countries[provinces[selected[0]].colour].name} ({countries[provinces[selected[0]].colour].tag})")
            else:
                standard_output(getattr(countries[provinces[selected[0]].colour], attr))
        else:
            standard_output(getattr(provinces[selected[0]], attr))
    elif current.lower()[0]=="o":
        output_destination=current.split(" ")[1]
    elif current.lower()[:3]=="exp":
        export()
    elif current.lower()[0] not in "nsrpcke":
        select_provinces(current)
    else:
        ind={"p":BW,"n":NORM,"s":SUB,"r":REG,"c":COU,"k":CONT,"e":EMP}[current.lower()]
        display_map(ind)

def scripting() -> None:
    EXIT=False
    while not EXIT and (current:=input()).lower() not in ("exit","end","quit","q","null"):
        try:
            if len(current)==0: continue
            if current.lower()[0]!="f":
                scripting_line(current)
            else:
                with open(current.split(" ")[1],"r") as file:
                    for line in file.read().splitlines():
                        if line in ("exit","end","quit","q","null"):
                            EXIT=True
                            break
                        scripting_line(line)
        except:
            On_Screen_Warning("General error occured during scripting!")
    sys.exit()

def standard_output(message: str) -> None:
    if output_destination=="console":
        print(message)
    else:
        with open(output_destination,"a") as file:
            file.write(message+"\n")

#Moving the map
def move(event) -> None:
    if is_additive or 0<additive_val<5: return
    global move_center

    def slide_map(vector: (int,int)) -> None:
        global map_position
        map_position=(sorted([-display_size[0],vector[0],int(scale*image_size[0])])[1],sorted([-display_size[1],vector[1],int(scale*image_size[1])])[1])
        images[displayed_map]=create_image(base[displayed_map])
        display_map(displayed_map)

    if move_center==None:
        move_center=(event.y+map_position[0],event.x+map_position[1])
        display_map(displayed_map)
    else:
        slide_map((move_center[0]-event.y,move_center[1]-event.x))

def clear_move_center(event) -> None:
    global move_center
    if move_center!=None:
        for i in range(len(images)):
            images[i]=create_image(base[i])
        display_map(displayed_map)
    move_center=None

zoom_cursor_position=(0,0)
last_point_position=(0,0)

def update_displayed_map(from_zoom=False) -> None:
    images[displayed_map]=create_image(base[displayed_map])
    display_map(displayed_map,from_zoom)

def increase_zoom(event) -> None:
    global scale
    scale+=0.5
    scale=sorted([round(scale,2),0.1,50])[1]
    update_displayed_map(True)

def decrease_zoom(event) -> None:
    global scale
    scale-=0.5
    scale=sorted([round(scale,2),0.1,50])[1]
    update_displayed_map(True)

def reset_zoom(event) -> None:
    global scale,map_position
    scale=1
    map_position=(0,0)
    update_displayed_map(True)

def zoom(event) -> None:
    if is_additive or 0<additive_val<5: return
    global scale, map_position, last_point_position, zoom_cursor_position
    #print(f"{event.x},{event.y},{event.num},{event.delta}")
    #last_point_position should be constant
    #if last_point_position!=(int((map_position[0]+event.y)/scale),int((map_position[1]+event.x)/scale)):
    #   map_position[0]=last_point_position[0]*scale-event.y
    if zoom_cursor_position==(event.y,event.x):
        if platform=="linux":
            delta=1 if event.num==4 else -1
            scale+=delta/20
        elif platform=="windows":
            scale+=(event.delta//120)/20
        scale=sorted([round(scale,2),0.1,50])[1]
        while image_size[0]*scale<display_size[0] or image_size[1]<display_size[1]:
            scale+=0.1
        map_position=(int(last_point_position[0]*scale-event.y),int(last_point_position[1]*scale-event.x))
    else:
        zoom_cursor_position=(event.y,event.x)
        last_point_position=(int((map_position[0]+event.y)/scale),int((map_position[1]+event.x)/scale))
    update_displayed_map(True)

def change_export_function():
    global quick_export
    quick_export=True

def remember_quick_export():
    #Write data to file
    with open("app_data.data","r") as file:
        is_last_linebreak=len(current:=file.read())>0 and current[-1]=="\n"
    with open("app_data.data","a") as file:
        if not is_last_linebreak:
            file.write("\n")
        file.write("quick_export\n")

quick_export=False

#Exporting
def bar():
    progress.grid(row=len(attributes)+4,column=1)
    root.config(cursor="watch")
    root.update()
    for i in range(3):
        progress['value'] = int(i*33)
        root.update_idletasks()
        time.sleep(0.9)

    progress['value'] = 100
    root.update_idletasks()
    time.sleep(0.9)

    progress.grid_forget()
    root.config(cursor="circle")

def export_information() -> None:
    with open(f"{ROOT}countries.txt","w") as file:
        for colour in countries:
            country=countries[colour]
            name=country.name if country.overlord==None else f"{country.name}-of-{country.overlord}"
            if country.civil_war!=None:
                file.write(f"{country.tag} {name} {country.colour} {country.civil_war}\n")
            else:
                file.write(f"{country.tag} {name} {country.colour}\n")
    with open(f"{ROOT}map_data.txt","w") as file:
        file.write(" ".join(headers)+"\n")
        for province in provinces:
            for header in headers:
                if header in attributes:
                    file.write(f"{getattr(province, header)} ")
                elif header=="position":
                    file.write(f"{province.pos[0]} {province.pos[1]} ")
                elif header=="box":
                    file.write(f"{province.box[0]} {province.box[1]} {province.box[2]} {province.box[3]} ")
                else:
                    file.write(f"{' '.join([str(i) for i in sorted(province.neighbours)])}")
            file.write("\n")
    cv2.imwrite(f"{ROOT}map.png",base[NORM])
    for i,attr in enumerate(attributes[2:]):
        cv2.imwrite(f"{ROOT}{attr if attr[-1]!='y' else attr[:-1]+'ie'}s.png",base[i+2])

def export() -> None:
    if not quick_export:
        root.after(1,bar)
    export_information()

#Export
progress = Progressbar(information[0], orient = tkinter.HORIZONTAL, length = display_size[0]//2, mode = 'determinate')
export_button=tkinter.Button(information[0],text="Export",command=export)
export_button.bind("<Return>",export)
with open("app_data.data","r") as file:
    if "quick_export" in file.read().splitlines():
        quick_export=True
    else:
        root.bind("<Control-i>", lambda e: [remember_quick_export(),change_export_function()]) #Instant export shortcut
export_button.grid(row=len(attributes)+3,column=1)

#Error message
error_message=tkinter.Label(root,bg="#FF7F7F",relief=tkinter.SOLID,borderwidth=2)

#Safety mechanism preventing the loss of large selections
is_additive=False
additive_val=0
def additive_pressed(event) -> None:
    global is_additive,additive_val
    additive_val+=1
    is_additive=True

def additive_released(event) -> None:
    global is_additive,additive_val
    additive_val-=1
    is_additive=False

#Binding functions
map_label.bind("<B1-Motion>", move) #Moving the map
map_label.bind("<ButtonRelease-1>",clear_move_center) #Finishing map movement
map_label.bind("<B2-Motion>", move) #Moving the map
map_label.bind("<ButtonRelease-2>",clear_move_center) #Finishing map movement
#Undo, redo
map_label.bind("<Control-z>", undo) #Undo
map_label.bind("<Control-y>", redo) #Redo
#Safety mechanism for larger selections (can't move on map while holding down shift or control)
map_label.bind("<Control_L>",additive_pressed)
map_label.bind("<KeyRelease-Control_L>",additive_released)
map_label.bind("<Control_R>",additive_pressed)
map_label.bind("<KeyRelease-Control_R>",additive_released)
map_label.bind("<Shift_L>",additive_pressed)
map_label.bind("<KeyRelease-Shift_L>",additive_released)
map_label.bind("<Shift_R>",additive_pressed)
map_label.bind("<KeyRelease-Shift_R>",additive_released)
#Zoom
if platform=="linux":
    map_label.bind("<Button-4>", zoom)
    map_label.bind("<Button-5>", zoom)
elif platform=="windows":
    map_label.bind("<MouseWheel>", zoom)
map_label.bind("<Control-plus>",increase_zoom)
map_label.bind("<Control-minus>",decrease_zoom)
map_label.bind("<Control-slash>",reset_zoom)
#Province selection
map_label.bind("<Button-1>", select_province) #Normal province selection
map_label.bind("<Control-Button-1>", lambda e: select_province(e,2)) #Additive prov. selection
map_label.bind("<Shift-Button-1>", lambda e: select_province(e,3)) #Decremental prov. selection
map_label.bind("<Button-3>", lambda e: select_province(e,1)) #One province at a time selection
map_label.bind("<Return>", select_neighbours)
#Map mode selection
map_label.bind("<p>", lambda e: display_map(BW)) #Black and white map
map_label.bind("<n>", lambda e: display_map(NORM)) #Normal map
if SUB>=0: map_label.bind("<s>", lambda e: display_map(SUB)) #Subregions
if REG>=0: map_label.bind("<r>", lambda e: display_map(REG)) #Regions
if COU>=0: map_label.bind("<c>", lambda e: display_map(COU)) #Countries (map mode)
if EMP>=0: map_label.bind("<e>", lambda e: display_map(EMP)) #Empires
if CONT>=0: map_label.bind("<k>", lambda e: display_map(CONT)) #Continents
for i in range(len(images)):
    map_label.bind(f"{i}", lambda e,i=i: display_map(i)) #Binding numbers to maps
#Switching between maps with up and down keys
map_label.bind("<Down>", lambda e: display_map((current_map-1)%len(images)))
map_label.bind("<Up>", lambda e: display_map((current_map+1)%len(images)))
#Shortcut to access information without clicking there
map_label.bind("<i>", lambda e: information[2][0].focus_set())

def exit_selection(event):
    display_map(NORM)

#Quality of Life bindings
root.bind("<Escape>", exit_selection)
root.bind_all('<Button>', change_focus)

#Global map information
provinces=get_provinces(f"{ROOT}map.png")
countries=get_countries(f"{ROOT}countries.txt")
unique_tags=[countries[i].tag for i in countries]
output_destination="console"
generate_countries()

#Fonts and settings
font_size=11
with open("app_data.data","r") as file:
    for i in file.read().splitlines():
        if "font_size" in i and "=" in i and i.split("=")[1].isnumeric():
            font_size=int(i.split("=")[1])
            break

def reload_all_widgets(root):
    for elem in root.winfo_children():
        if type(elem) in (tkinter.Label,tkinter.Button,tkinter.Entry):
            reload_font(elem)
        elif type(elem)==tkinter.Frame:
            reload_all_widgets(elem)

def reload_font(widget):
   widget.config(font=('Helvetica', font_size))

def change_font_size(value):
    global font_size
    font_size=value
    reload_all_widgets(root)

reload_all_widgets(root)

#Scripting
root.after(1,scripting)

#Closing properly
def on_closing():
    root.destroy()
    sys.exit()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()