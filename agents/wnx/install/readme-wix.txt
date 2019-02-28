Add this to the end pf Product    
    
    <!-- Step 2: Add files to your installer package -->
    <DirectoryRef Id="binid">
      <Component Id="check_mk_data"
                  Guid="{382114FC-FB0C-4A15-AECE-CD489957DDFC}">
        <File Id="check_mk.dat"
              Source="resources\check_mk.dat"
              Name="check_mk.dat"
              KeyPath="yes"
              Checksum="yes"
              />
      </Component>
    </DirectoryRef>

    <!-- Step 3: Tell WiX to install the files -->
    <Feature Id="placeholder" Title="Just Placeholder" Level="1">
      <ComponentRef Id="check_mk_data" />
    </Feature>


