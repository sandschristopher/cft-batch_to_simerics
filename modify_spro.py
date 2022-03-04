from re import search
from itertools import chain

def modify_spro(spro_file, stage_components):

    # Gets patch names for each componenet:
    patches = []
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if "<mgi name=" in line:
                MGI_tuple = (data[line_number + 1].split("\"")[1],  data[line_number + 2].split("\"")[1])
                patches.append(MGI_tuple)
        
        for line_number, line in enumerate(data):
            if "plot.DPtt = " in line:
                patches.insert(0, line.split("\"")[3])
                patches.append(line.split("\"")[1])

    # Gets the mismatched grid interface names:
    MGIs = []
    with open(spro_file, 'r') as infile:
        for line in infile.readlines():
            if "patch=\"MGI" in line:
                MGIs.append(line.strip().split("\"")[1])

    # Gets the interface names for each control volume:
    CVIs = list(MGIs)
    with open(spro_file, 'r') as infile:
        for line in infile.readlines():
            if "plot.DPtt = " in line:
                CVIs.insert(0, line.split("\"")[3])
                CVIs.append(line.split("\"")[1])

    # Gets name/number associated with impellers:
    impellers = []
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if "#plot.PC" in line and "imp" in line:
                impeller_number = search("#plot.PC(\d)", line).group(1)
                impeller_name = data[line_number - 1].split("\"")[1].split("-")[0]
                impellers.append((impeller_name, impeller_number))

    stage_patches = list(chain(*patches[(stage_components[0] - 1):(stage_components[-1] + 1)]))

    stage_power_components = []

    for patch in stage_patches[1:-1]:
        for impeller in impellers:
            if impeller[0] in patch:
                stage_power_components.append("plot.PC" + impeller[1])

    stage_power_components = list(set(stage_power_components))
    
    if len(stage_power_components) == 0:
        stage_power = False
    elif len(stage_power_components) == 1:
        stage_power = stage_power_components[0]
    else:
        stage_power = " + ".join(stage_power_components)

    # Gets the indentation of each expression:
    with open(spro_file, 'r') as infile:
        for line in infile.readlines():
            if "#Outlet volumetric flux [m3/s]" in line or "#Mass flow [kg/s]" in line:
                indent = line.split("#")[0]
                break

    # Ensures consistent .sgrd file:
    with open(spro_file, 'r') as infile:
        data = infile.readlines()
        for line_number, line in enumerate(data):
            if ".sgrd" in line:
                data[line_number] = line.replace("transient", "steady")
                break
    
    # Gets name of leakage interface:
        with open(spro_file, 'r') as infile:
            for line in infile.readlines():
                if "OutletInterface" in line:
                    leakage_interface = line.split("\"")[1].strip()
                else:
                    leakage_interface = 0

    with open(spro_file, 'w') as outfile:
        data = "".join(data)
        outfile.write(data)
    
    def insert_line(addition):

        exists_already = False

        with open(spro_file, 'r') as infile:
            data = infile.readlines()
            for line_number, line in enumerate(data):
                if addition.split("\n")[0].strip() in line:
                    exists_already = True
                    
        if exists_already == False:
            with open(spro_file, 'r') as infile:
                data = infile.readlines()
                for line_number, line in enumerate(data):
                    if "</expressions>" in line:
                        data.insert(line_number, "\n" + addition + "\n")
                        break

            with open(spro_file, 'w') as outfile:
                data = "".join(data)
                outfile.write(data)

    insert_line(indent + "#head [m]" + "\n" + indent + "plot.H = plot.DPtt/rho/9.81 \n" + indent + "#plot.H:head [m]")

    insert_line(indent + "#delta p (t-t), stage [Pa]" + "\n" + indent + "plot.DPtt_stage = flow.mpt@\"" \
        + CVIs[stage_components[-1]] + "\" - flow.mpt@\"" + CVIs[(stage_components[0] - 1)] + "\"\n" + indent + "#plot.DPtt_stage:delta p (t-t), stage [Pa]")
    
    if stage_power != False:
        insert_line(indent + "#efficiency (t-t), stage [-]" + "\n" + indent + "plot.Eff_tt_stage = flow.q@\"" \
            + CVIs[stage_components[-1]] + "\"*plot.DPtt_stage/rho/(" + stage_power + ")\n" + indent + "#plot.Eff_tt_stage:efficiency (t-t), stage [-]")

    for i in range(1, len(CVIs)):
        insert_line(indent + "#delta p (t-t), CV" + str(i) + " [Pa]" + "\n" + indent + "plot.DPttCV" + str(i) + " = flow.mpt@\"" \
            + CVIs[i] + "\" - flow.mpt@\"" + CVIs[i - 1] + "\"\n" + indent + "#plot.DPttCV" + str(i) + ":delta p (t-t), CV" \
            + str(i) + " [Pa]")

        insert_line(indent + "#delta p (t-s), CV" + str(i) + " [Pa]" + "\n" + indent + "plot.DPtsCV" + str(i) + " = flow.p@\"" \
            + CVIs[i] + "\" - flow.p@\"" + CVIs[i - 1] + "\"\n" + indent + "#plot.DPtsCV" + str(i) + ":delta p (t-s), CV" \
            + str(i) + " [Pa]")

    if leakage_interface != 0:

        insert_line(indent + "#mass flow, shroud leakage, relative [-]" + "\n" + indent + "plot.mShroudLeakageRel = (flow.q@\"" \
            + leakage_interface + "\" - flow.q@\"" + CVIs[-1] + "\")/(flow.q@\"" + CVIs[-1] + "\")" + "\n" + indent + "#plot.mShroudLeakageRel:mass flow, shroud leakage, relative [-]")

        insert_line(indent + "#mass flow, shroud leakage, absolute [kg/s]" + "\n" + indent + "plot.mShroudLeakageAbs = flow.q@\"" \
            + leakage_interface + "\" - flow.q@\"" + CVIs[-1] + "\"\n" + indent + "#plot.mShroudLeakageAbs:mass flow, shroud leakage, absolute [kg/s]")

        insert_line(indent + "#volumetric flow, shroud leakage, relative [-]" + "\n" + indent + "plot.vShroudLeakageRel = (flow.qv@\"" \
            + leakage_interface + "\" - flow.qv@\"" + CVIs[-1] + "\")/(flow.qv@\"" + CVIs[-1] + "\")" + "\n" + indent + "#plot.vShroudLeakageRel:volumetric flow, shroud leakage, relative [-]")

        insert_line(indent + "#volumetric flow, shroud leakage, absolute [m3/s]" + "\n" + indent + "plot.vShroudLeakageAbs = flow.qv@\"" \
            + leakage_interface + "\" - flow.qv@\"" + CVIs[-1] + "\"\n" + indent + "#plot.vShroudLeakageAbs:volumetric flow, shroud leakage, absolute [m3/s]")

        insert_line(indent + "#efficiency (t-t), imp1 passage [-]" + "\n" + indent + "plot.Eff_tt_" + impeller_number + "Passage = flow.qv@\"" \
            + leakage_interface + "\"*plot.DPtt" + impeller_number + "Passage/plot.PC" + impeller_number + "Passage" + "\n" + indent + "#plot.Eff_tt_" + impeller_number + "Passage:efficiency (t-t), imp1 passage [-]")

        insert_line(indent + "#power, imp1 passage [W]" + "\n" + indent + "plot.PC" + impeller_number + "Passage = abs(flow.power@\"" + impeller_name + "-Hub\"" \
            + " + flow.power@\"" + impeller_name + "-Shroud\" + flow.power@\"" + impeller_name + "-BladeSides\" + flow.power@\"" + impeller_name + "-BladeLE\" + flow.power@\"" + impeller_name + "-BladeTE\")" \
            + "\n" + indent + "#plot.PC" + impeller_number + "Passage:power, imp1 passage [W]")

        insert_line(indent + "#delta p (t-t), imp1 passage [Pa]" + "\n" + indent + "plot.DPtt2Passage = flow.mpt@\"" \
            + leakage_interface + "\" - flow.mpt@\"" + MGIs[0] + "\"\n" + indent + "#plot.DPtt2Passage:delta p (t-t), imp1 passage [Pa]")

        insert_line(indent + "#volumetric flow, OutletInterface, absolute [m3/s]" + "\n" + indent + "plot.vOutletInterface = flow.qv@\"" \
            + leakage_interface + "\"\n" + indent + "#plot.vOutletInterface:#volumetric flow, OutletInterface, absolute [m3/s]")

        insert_line(indent + "#volumetric flow, OutletExtension, absolute [m3/s]" + "\n" + indent + "plot.vOutletExtension = flow.qv@\"" \
            + CVIs[-1] + "\"\n" + indent + "#plot.vOutletExtension:#volumetric flow, OutletExtension, absolute [m3/s]")

    return 0

def get_Dicts(spro_file):

    with open(spro_file, "r") as infile:
        units_Dict = {}
        desc_Dict = {}
        data = infile.readlines()
        for line in data:
            if "#plot." in line:
                key = line.split(":")[0].split(".")[1].strip()
                units_Dict[key] = line.split(" ")[-1].strip() 
                desc_Dict[key] = line.split("[")[0].split(":")[1].strip()

    return units_Dict, desc_Dict

modify_spro("CRDF_v01_transient_8000rpm_1-25m3s.spro", [1, 2])