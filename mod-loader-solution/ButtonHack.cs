﻿using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
public class ButtonHack : MonoBehaviour
{
    public float alphaThreshold = 0.1f;
    void Start()
    {
        this.GetComponent<Image>().alphaHitTestMinimumThreshold = alphaThreshold;
    }
    public void deez()
    {
        int x = 0;
        x = x;   // CS1717  
    }
}
